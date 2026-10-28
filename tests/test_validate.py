from pathlib import Path

import pytest
import yaml

from cvgen.cli import main
from cvgen.load import load_yaml

EXAMPLE = Path(__file__).parents[1] / "examples" / "content"


def write_cv(tmp_path, mutate):
    """Load the example, apply `mutate(data)`, write it to tmp_path/cv.yaml and return its text."""
    data, _ = load_yaml(EXAMPLE / "cv.yaml")
    mutate(data)
    text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    (tmp_path / "cv.yaml").write_text(text, encoding="utf-8")
    return text


def line_of(text, needle):
    return next(i for i, line in enumerate(text.splitlines(), 1) if needle in line)


def run(capsys, *argv):
    code = main(["validate", *argv])
    return code, capsys.readouterr().out


@pytest.mark.parametrize("locale", [[], ["--locale", "en"], ["--locale", "da"]])
def test_example_is_valid(capsys, locale):
    code, out = run(capsys, "--content", str(EXAMPLE), *locale)
    assert code == 0, out


@pytest.mark.parametrize("key", ["name", "email", "phone", "url", "image", "location", "profiles"])
def test_forbidden_basics_key(tmp_path, capsys, key):
    text = write_cv(tmp_path, lambda d: d["basics"].update({key: "x"}))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, f'{key}: x')}: pii/key:" in out
    assert "schema/" not in out  # reported once, by the PII guard


PII_VALUES = [
    ("pii/email", "someone@example.com"),
    ("pii/phone", "+1 555 010 0123"),
    ("pii/phone", "12 34 56 78"),
    ("pii/phone", "12-34-56-78"),
    ("pii/phone", "1234 5678"),
    ("pii/phone", "2012 2034"),
    ("pii/phone", "4512345678"),
    ("pii/phone", "0045 12345678"),
    ("pii/cpr", "010190-1234"),
    ("pii/cpr", "010190 1234"),
    ("pii/profile-url", "https://www.linkedin.com/in/someone-example"),
    ("pii/profile-url", "dk.linkedin.com/in/someone-example"),
    ("pii/profile-url", "https://linkedin.com/pub/someone/1/2/3"),
]
PII_PLACES = {
    "localized-in-list": lambda d, v: d["work"][1]["highlights"][1].update({"da": f"Kontakt {v} for mere."}),
    "nested-bullet": lambda d, v: d["x-narrative"][0]["bullets"][0]["text"].update({"en": f"See {v}"}),
    "plain-string": lambda d, v: d["education"][0].update({"institution": v}),
    "list-item": lambda d, v: d["interests"][1].update({"keywords": ["a", v]}),
}


@pytest.mark.parametrize("place", PII_PLACES)
@pytest.mark.parametrize("rule, value", PII_VALUES)
def test_pii_pattern(tmp_path, capsys, rule, value, place):
    text = write_cv(tmp_path, lambda d: PII_PLACES[place](d, value))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, value)}: {rule}:" in out
    assert value not in out


def test_pii_in_key_is_reported_and_masked(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["work"][0].update({"someone@example.com": "x"}))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, 'someone@example.com')}: pii/email:" in out
    assert "someone@example.com" not in out


@pytest.mark.parametrize(
    "rule, number",
    [
        ("pii/phone", "12345678"),
        ("pii/phone", "+4512345678"),
        ("pii/phone", "4512345678"),
        ("pii/cpr", "0101901234"),
    ],
)
def test_pii_in_unquoted_number(tmp_path, capsys, rule, number):
    raw = f"schemaVersion: 1\nbasics: {{}}\nx-narrative:\n  - id: a\n    title: T\n    body: {number}\n"
    (tmp_path / "cv.yaml").write_text(raw, encoding="utf-8")
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:6: {rule}:" in out
    assert number not in out


@pytest.mark.parametrize(
    "raw, locale",
    [
        ("schemaVersion: 1\nbasics: {}\nwork: [{name: A, startDate: '2020', Anna Hansen: x}]\n", None),
        (
            "schemaVersion: 1\nbasics: {}\nwork: [{name: A, startDate: '2020', Anna Hansen: x, "
            "Anna Hansen: y}]\n",
            None,
        ),
        ("schemaVersion: 1\nbasics: {}\nx-narrative: [{id: a, title: T, Anna Hansen: {en: x}}]\n", "de"),
        ("schemaVersion: 1\nbasics: {}\nwork: [{name: A, startDate: '2020', Anna: x}]\n", None),
        ("schemaVersion: 1\nbasics: {}\nx-narrative: [{id: a, title: {en: T, Anna: U}}]\n", "de"),
        ("schemaVersion: 1\nbasics: {}\nwork: [{name: A, startDate: '2020', eva: x}]\n", None),
        ("schemaVersion: 1\nbasics: {}\nwork: [{name: A, startDate: '2020', jan: {en: x}}]\n", "de"),
    ],
)
def test_keys_that_are_not_identifiers_are_never_printed(tmp_path, capsys, raw, locale):
    (tmp_path / "cv.yaml").write_text(raw, encoding="utf-8")
    code, out = run(capsys, "--content", str(tmp_path), *(["--locale", locale] if locale else []))
    assert code == 1
    for name in ("Anna", "eva", "jan"):
        assert name not in out


def test_no_false_positives_on_years_and_percentages(tmp_path, capsys):
    def mutate(d):
        d["basics"]["summary"]["en"] = (
            "From 2011 - 2017 and 2018-2024 I served 90% of 1200 users in 3 countries; see netflix.com/x."
        )

    write_cv(tmp_path, mutate)
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 0, out


def test_schema_error_has_line(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["work"][1].pop("startDate"))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, 'id: contoso')}: schema/required:" in out
    assert "startDate" in out


def test_unknown_key_is_rejected(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["work"][0].update({"startdate": "2020-01", "issuer": "x"}))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    # reported on the key's own line; shown only when it is a key the schema knows elsewhere
    assert (
        f"cv.yaml:{line_of(text, 'startdate:')}: schema/unexpected-key: work[0]: unexpected key '***'" in out
    )
    assert (
        f"cv.yaml:{line_of(text, 'issuer:')}: schema/unexpected-key: work[0]: unexpected key 'issuer'" in out
    )


def test_missing_translation(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["projects"][1]["description"].pop("da"))
    code, out = run(capsys, "--content", str(tmp_path), "--locale", "da")
    assert code == 1
    found = [ln for ln in out.splitlines() if "i18n/missing" in ln]
    rows = text.splitlines()
    project = line_of(text, "name: Tailspin Logistics")
    expected = next(i for i in range(project, len(rows) + 1) if "description:" in rows[i - 1])
    assert found == [
        f"{tmp_path / 'cv.yaml'}:{expected}: i18n/missing: projects[1].description has no 'da' text"
    ]


def test_unknown_employer_reference(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["projects"][0].update({"x-employer": "nobody"}))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, 'x-employer: nobody')}: ref/employer:" in out


def test_yaml_12_scalars(tmp_path):
    raw = (
        "a: no\nb: 2024-03-01\nc: yes\nd: true\ne: 3\nf: ~\ng: 1_000\nh: 1e3\ni: 0x1F\nj: 'q'\n"
        "k: +1\nl: +4512345678\n"
    )
    (tmp_path / "x.yaml").write_text(raw, encoding="utf-8")
    data, lines = load_yaml(tmp_path / "x.yaml")
    assert data == {
        "a": "no", "b": "2024-03-01", "c": "yes", "d": True, "e": 3, "f": None,
        "g": "1_000", "h": 1000.0, "i": 31, "j": "q", "k": 1, "l": "+4512345678",
    }  # fmt: skip
    assert lines[("b",)] == 2


def test_yaml_12_language_code_no_validates(tmp_path, capsys):
    write_cv(tmp_path, lambda d: d["languages"].append({"language": "no", "fluency": "B1"}))
    file = tmp_path / "cv.yaml"
    file.write_text(
        file.read_text(encoding="utf-8").replace("language: 'no'", "language: no"), encoding="utf-8"
    )
    assert "language: no\n" in file.read_text(encoding="utf-8")  # unquoted, as a person would write it
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 0, out


def test_duplicate_key(tmp_path, capsys):
    (tmp_path / "cv.yaml").write_text("schemaVersion: 1\nbasics: {}\nbasics: {}\n", encoding="utf-8")
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert "cv.yaml:3: yaml/duplicate-key:" in out


@pytest.mark.parametrize(
    "raw, rule",
    [
        (b"schemaVersion: 1\nbasics: {}\n? [a]\n: b\n", "yaml/key"),
        (b"schemaVersion: 1\nbasics: &a {label: *a}\n", "yaml/recursive-alias"),
        (b"schemaVersion: 1\nbasics: {}\nwork: 5\nprojects: 5\n", "schema/type"),
        (b'schemaVersion: 1\nbasics: {label: "a\x01b"}\n', "yaml/syntax"),
        (b"schemaVersion: 1\nbasics: {label: \xff\xfe}\n", "yaml/encoding"),
        (
            b"schemaVersion: 1\nbasics: {}\nwork: [{id: a, name: A, startDate: '2020'}]\n"
            b"projects: [{name: P, x-employer: [a]}]\n",
            "schema/type",
        ),
    ],
)
def test_bad_input_is_a_finding_not_a_crash(tmp_path, capsys, raw, rule):
    (tmp_path / "cv.yaml").write_bytes(raw)
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f": {rule}:" in out


def test_missing_content_file(tmp_path, capsys):
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 2
    assert "cv.yaml" in out


def test_entry_date_key_is_unexpected_outside_entries(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["certificates"][0].update({"startDate": "1999"}))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    expected = "schema/unexpected-key: certificates[0]: unexpected key 'startDate'"
    assert f"cv.yaml:{line_of(text, "startDate: '1999'")}: {expected}" in out
