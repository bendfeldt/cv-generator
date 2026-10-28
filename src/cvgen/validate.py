"""Check CV content: JSON Schema, the PII guard, translations and references. Findings never echo values."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from cvgen.load import KeyPath, LoadError, load_yaml

# shortcut: schemas are read from the repo checkout, fine under `uv run`; package them if cvgen is published.
SCHEMAS = Path(__file__).parents[2] / "schemas"
SCHEMA = json.loads((SCHEMAS / "content.schema.json").read_text(encoding="utf-8"))
LANG = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")


def _property_names(node: Any) -> set[str]:
    if isinstance(node, list):
        return set().union(*map(_property_names, node))
    if not isinstance(node, dict):
        return set()
    own = set(node.get("properties", {}))
    return own.union(*map(_property_names, node.values()))


KNOWN_KEYS = _property_names(SCHEMA)  # the only keys safe to print: the schema's own vocabulary
ENTRY_META_KEYS = set(SCHEMA["$defs"]["entryMeta"]["properties"])

PII_KEYS = {"name", "email", "phone", "url", "image", "location", "profiles"}  # forbidden under basics
PII_PATTERNS = {
    "pii/email": re.compile(r"[\w.%+-]+@[\w-]+(\.[\w-]+)*\.[a-z]{2,}", re.I),
    # international; Danish 12 34 56 78 / 12-34-56-78 / 1234 5678 / 12345678; 2018-2024 is a year range.
    "pii/phone": re.compile(
        r"\+\d[\d ().-]{6,}\d|\b\d{2}([ .-]?)\d{2}\1\d{2}\1\d{2}\b"
        r"|\b(?!(19|20)\d\d-(19|20)\d\d\b)\d{4}[ .-]\d{4}\b"
    ),
    "pii/cpr": re.compile(r"\b(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])\d{2}[ -]?\d{4}\b"),
    "pii/profile-url": re.compile(
        r"(?<![\w-])([\w-]+\.)*(linkedin\.com/(in|pub)|xing\.com/profile|facebook\.com|instagram\.com|twitter\.com|x\.com)/",
        re.I,
    ),
}


@dataclass(frozen=True)
class Finding:
    file: Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.rule}: {self.message}"


def _key(key: str) -> str:
    """A key fit to print: one the schema defines. Anything else, even a language code, may be a name."""
    return key if key in KNOWN_KEYS else "***"


def dotted(path: KeyPath) -> str:
    out = ""
    for part in path:
        out += f"[{part}]" if isinstance(part, int) else f".{_key(part)}" if out else _key(part)
    return out or "(root)"


def _walk(value: Any, at: KeyPath = ()):
    yield at, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, (*at, key))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _walk(child, (*at, i))


def _is_localized(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(isinstance(k, str) and LANG.match(k) and isinstance(v, str) for k, v in value.items())
    )


def _pii_rules(text: str) -> list[str]:
    return [rule for rule, pattern in PII_PATTERNS.items() if pattern.search(text)]


def _mask(text: str) -> str:
    for pattern in PII_PATTERNS.values():
        text = pattern.sub("***", text)
    return text


def _schema_message(err) -> str:
    if err.validator is None:
        return "not allowed here"
    if err.validator == "required":
        return err.message  # names schema keys only
    if err.validator == "anyOf":
        return "is neither a string, a {en: ..., da: ...} map, nor an allowed object"
    return f"fails {err.validator} {json.dumps(err.validator_value)}"


def validate_content(file: Path, locale: str | None = None) -> list[Finding]:
    try:
        data, lines = load_yaml(file)
    except LoadError as e:
        return [Finding(file, e.line, e.rule, str(e))]
    except yaml.MarkedYAMLError as e:
        line = e.problem_mark.line + 1 if e.problem_mark else 1
        return [Finding(file, line, "yaml/syntax", e.problem or "invalid YAML")]
    except yaml.reader.ReaderError as e:  # e.g. a control character
        line = file.read_text(encoding="utf-8")[: e.position].count("\n") + 1
        return [Finding(file, line, "yaml/syntax", f"character U+{e.character:04X} is not allowed in YAML")]

    def line(path: KeyPath) -> int:
        while path not in lines:
            path = path[:-1]
        return lines[path]

    findings: list[Finding] = []
    basics = data.get("basics") if isinstance(data, dict) else None
    pii_paths = {("basics", k) for k in basics if k in PII_KEYS} if isinstance(basics, dict) else set()
    for path in sorted(pii_paths):
        findings.append(
            Finding(
                file, line(path), "pii/key", f"{dotted(path)} is personal data; it is asked for at build time"
            )
        )

    # PII keys are reported above; jsonschema would report them again, without naming the key.
    checked = (
        {**data, "basics": {k: v for k, v in basics.items() if k not in PII_KEYS}} if pii_paths else data
    )
    for err in Draft202012Validator(SCHEMA).iter_errors(checked):
        path = tuple(err.absolute_path)
        if err.validator in ("additionalProperties", "unevaluatedProperties"):
            # one finding per unexpected key, on its own line, since the key itself may not be printable
            allowed = set(err.schema.get("properties", {}))
            if err.validator == "unevaluatedProperties":  # entries: their own keys plus entryMeta
                allowed |= ENTRY_META_KEYS
            for key in (k for k in err.instance if k not in allowed):
                message = f"{dotted(path)}: unexpected key '{_key(key)}'"
                findings.append(Finding(file, line((*path, key)), "schema/unexpected-key", message))
            continue
        findings.append(
            Finding(
                file,
                line(path),
                f"schema/{err.validator or 'forbidden'}",
                _mask(f"{dotted(path)}: {_schema_message(err)}"),
            )
        )

    for path, value in _walk(data):
        if path and isinstance(path[-1], str):
            for rule in _pii_rules(path[-1]):
                findings.append(
                    Finding(file, line(path), rule, f"a key in {dotted(path[:-1])} contains personal data")
                )
        # numbers too: an unquoted 12345678 is an int, not a string
        if isinstance(value, str | int | float) and not isinstance(value, bool):
            for rule in _pii_rules(str(value)):
                findings.append(Finding(file, line(path), rule, f"{dotted(path)} contains personal data"))
        if locale and _is_localized(value) and locale not in value:
            findings.append(
                Finding(file, line(path), "i18n/missing", f"{dotted(path)} has no '{locale}' text")
            )

    if isinstance(data, dict):
        work, projects = data.get("work"), data.get("projects")
        ids = {w.get("id") for w in work if isinstance(w, dict)} if isinstance(work, list) else set()
        for i, project in enumerate(projects if isinstance(projects, list) else []):
            employer = project.get("x-employer") if isinstance(project, dict) else None
            if isinstance(employer, str) and employer not in ids:
                path = ("projects", i, "x-employer")
                findings.append(
                    Finding(file, line(path), "ref/employer", f"{dotted(path)} names no work entry id")
                )

    return sorted(findings, key=lambda f: (f.line, f.rule))
