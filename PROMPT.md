# Goal
A CLI that builds a CV (PDF, HTML, JSON Resume, JSON-LD, Markdown, text) from YAML content, profile, theme and locale files, asking for all personal data at runtime and storing none of it. Full plan: `docs/PLAN.md`.

## Done when
- `uv run pytest` and `uv run ruff check .` are green.
- `uv run cvgen validate --content examples/content` exits 0, and every fixture in `tests/fixtures/pii/` exits 1.
- `CVGEN_PII_*=<synthetic> uv run cvgen build --profile full-en --content examples/content --no-input` writes all six formats to `out/`.
- Every entry in `feature_list.json` has `passes: true`.

## Never touch
- `private/`, `out/` (owner's real data and generated CVs).
- `.claude/skills/` content (vendored; see THIRD_PARTY_NOTICES.md) except through an explicit update.
- The PII guard rules, except to make them stricter.

## Stop if
- Any change would store a personal value in a tracked file.
- A passing test starts failing.
- More than 10 files outside the current phase's scope change.
