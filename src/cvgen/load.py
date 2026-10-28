"""Load YAML with the line of every key and list item, so findings can point at file:line."""

from pathlib import Path
from typing import Any

import yaml

KeyPath = tuple[str | int, ...]


class DuplicateKeyError(ValueError):
    def __init__(self, key: str, line: int):
        super().__init__(f"key '{key}' appears twice in the same mapping")
        self.line = line


def _scalar(node: yaml.ScalarNode) -> Any:
    # YAML 1.2 core schema on top of PyYAML's 1.1 resolver: only true/false are booleans
    # ("no" is Norway's language code) and dates stay strings, as JSON Resume expects.
    if node.style is not None:  # quoted or block scalar
        return node.value
    kind, value = node.tag.rsplit(":", 1)[-1], node.value
    if kind == "null":
        return None
    if kind == "bool" and value.lower() in ("true", "false"):
        return value.lower() == "true"
    if kind == "int":
        try:
            return int(value, 0)
        except ValueError:
            return value
    if kind == "float":
        try:
            return float(value)
        except ValueError:
            return value
    return value


def load_yaml(path: Path) -> tuple[Any, dict[KeyPath, int]]:
    """Return (data, lines): `lines` maps a path such as ("work", 0, "name") to its 1-based line."""
    lines: dict[KeyPath, int] = {(): 1}

    def build(node: yaml.Node, at: KeyPath) -> Any:
        if isinstance(node, yaml.MappingNode):
            out: dict[str, Any] = {}
            for key_node, value_node in node.value:
                key = key_node.value
                if key in out:
                    raise DuplicateKeyError(key, key_node.start_mark.line + 1)
                lines[(*at, key)] = key_node.start_mark.line + 1
                out[key] = build(value_node, (*at, key))
            return out
        if isinstance(node, yaml.SequenceNode):
            items = []
            for i, item in enumerate(node.value):
                lines[(*at, i)] = item.start_mark.line + 1
                items.append(build(item, (*at, i)))
            return items
        return _scalar(node)

    root = yaml.compose(Path(path).read_text(encoding="utf-8"), Loader=yaml.SafeLoader)
    return (build(root, ()) if root is not None else None), lines
