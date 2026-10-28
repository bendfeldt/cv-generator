"""Load YAML with the line of every key and list item, so findings can point at file:line."""

import re
from pathlib import Path
from typing import Any

import yaml

KeyPath = tuple[str | int, ...]

# YAML 1.2 core schema (PyYAML resolves YAML 1.1, where `no` is false and `1_000` is an int).
_NULL = re.compile(r"~|null|Null|NULL|")
_BOOL = re.compile(r"true|True|TRUE|false|False|FALSE")
_INT = re.compile(r"[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+")
_FLOAT = re.compile(
    r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?|[-+]?\.(inf|Inf|INF)|\.(nan|NaN|NAN)"
)


class LoadError(ValueError):
    def __init__(self, rule: str, message: str, line: int = 1):
        super().__init__(message)
        self.rule, self.line = rule, line


def _scalar(node: yaml.ScalarNode) -> Any:
    value = node.value
    if node.style is not None:  # quoted or block scalar: always a string
        return value
    if _NULL.fullmatch(value):
        return None
    if _BOOL.fullmatch(value):
        return value.lower() == "true"
    if _INT.fullmatch(value):
        return int(value, 0) if value[:2] in ("0o", "0x") else int(value)
    if _FLOAT.fullmatch(value):
        return float(value.lower().replace(".inf", "inf").replace(".nan", "nan"))
    return value


def load_yaml(path: Path) -> tuple[Any, dict[KeyPath, int]]:
    """Return (data, lines): `lines` maps a path such as ("work", 0, "name") to its 1-based line.

    Raises LoadError for anything that is not plain YAML data; yaml.YAMLError for syntax errors.
    """
    lines: dict[KeyPath, int] = {(): 1}
    open_nodes: set[int] = set()

    def build(node: yaml.Node, at: KeyPath) -> Any:
        if id(node) in open_nodes:
            raise LoadError(
                "yaml/recursive-alias", "an alias refers to a node that contains it", node.start_mark.line + 1
            )
        if isinstance(node, yaml.ScalarNode):
            return _scalar(node)
        open_nodes.add(id(node))
        try:
            if isinstance(node, yaml.MappingNode):
                out: dict[str, Any] = {}
                for key_node, value_node in node.value:
                    key_line = key_node.start_mark.line + 1
                    if not isinstance(key_node, yaml.ScalarNode):
                        raise LoadError("yaml/key", "keys must be plain strings", key_line)
                    key = key_node.value
                    if key in out:
                        raise LoadError(
                            "yaml/duplicate-key", f"key '{key}' appears twice in the same mapping", key_line
                        )
                    lines[(*at, key)] = key_line
                    out[key] = build(value_node, (*at, key))
                return out
            items = []
            for i, item in enumerate(node.value):
                lines[(*at, i)] = item.start_mark.line + 1
                items.append(build(item, (*at, i)))
            return items
        finally:
            open_nodes.discard(id(node))

    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise LoadError("yaml/encoding", f"file is not UTF-8 (byte {e.start})") from None
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    return (build(root, ()) if root is not None else None), lines
