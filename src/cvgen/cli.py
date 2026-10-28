"""cvgen command line."""

import argparse
from pathlib import Path

from cvgen.validate import LANG, validate_content


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cvgen", description="Build a CV from YAML. Personal data is asked for at build time."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check content: schema, personal data guard, translations")
    v.add_argument("--content", type=Path, required=True, help="directory holding cv.yaml")
    v.add_argument("--locale", help="also report text missing in this language, e.g. da")
    args = parser.parse_args(argv)

    if args.locale and not LANG.match(args.locale):
        print(f"--locale: '{args.locale}' is not a BCP 47 language code such as en or da")
        return 2
    file = args.content / "cv.yaml"
    if not file.is_file():
        print(f"{file}: not found")
        return 2
    findings = validate_content(file, args.locale)
    for finding in findings:
        print(finding)
    if findings:
        print(f"{len(findings)} problem(s) in {file}")
        return 1
    print(f"OK: {file}")
    return 0
