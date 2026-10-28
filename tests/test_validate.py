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


@pytest.mark.parametrize(
    "rule, value",
    [
        ("pii/email", "someone@example.com"),
        ("pii/phone", "+1 555 010 0123"),
        ("pii/phone", "12 34 56 78"),
        ("pii/cpr", "010190-1234"),
        ("pii/profile-url", "https://www.linkedin.com/in/someone-example"),
    ],
)
def test_pii_pattern(tmp_path, capsys, rule, value):
    def mutate(d):
        d["work"][1]["highlights"][1]["da"] = f"Kontakt {value} for mere."

    text = write_cv(tmp_path, mutate)
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, value)}: {rule}:" in out
    assert value not in out


def test_no_false_positives_on_years_and_percentages(tmp_path, capsys):
    def mutate(d):
        d["basics"]["summary"]["en"] = (
            "From 2011 - 2017 and 2018-2024 I served 90% of 1200 users in 3 countries."
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
    text = write_cv(tmp_path, lambda d: d["work"][0].update({"startdate": "2020-01"}))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, 'id: northwind')}: schema/" in out


def test_missing_translation(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["projects"][1]["description"].pop("da"))
    code, out = run(capsys, "--content", str(tmp_path), "--locale", "da")
    assert code == 1
    lines = [ln for ln in out.splitlines() if "i18n/missing" in ln]
    assert len(lines) == 1
    assert lines[0].startswith(
        f"{tmp_path / 'cv.yaml'}:{line_of(text, 'Core data model') - 1}: i18n/missing:"
    )
    assert "projects[1].description" in lines[0]


def test_unknown_employer_reference(tmp_path, capsys):
    text = write_cv(tmp_path, lambda d: d["projects"][0].update({"x-employer": "nobody"}))
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert f"cv.yaml:{line_of(text, 'x-employer: nobody')}: ref/employer:" in out


def test_yaml_12_scalars(tmp_path):
    (tmp_path / "x.yaml").write_text("a: no\nb: 2024-03-01\nc: yes\nd: true\ne: 3\nf: ~\n", encoding="utf-8")
    data, lines = load_yaml(tmp_path / "x.yaml")
    assert data == {"a": "no", "b": "2024-03-01", "c": "yes", "d": True, "e": 3, "f": None}
    assert lines[("b",)] == 2


def test_duplicate_key(tmp_path, capsys):
    (tmp_path / "cv.yaml").write_text("schemaVersion: 1\nbasics: {}\nbasics: {}\n", encoding="utf-8")
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 1
    assert "cv.yaml:3: yaml/duplicate-key:" in out


def test_missing_content_file(tmp_path, capsys):
    code, out = run(capsys, "--content", str(tmp_path))
    assert code == 2
    assert "cv.yaml" in out
