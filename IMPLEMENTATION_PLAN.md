STATUS: in-progress

# Implementation plan
Phases and contracts: `docs/PLAN.md` §6. Feature ledger: `feature_list.json`.

## Done
- Phase 0: harness, skills, plan, research.
- Decisions recorded in `docs/PLAN.md` §7 (private repo, `{en, da}` strings, LuaLaTeX, no HTML in v1).

## Sprint contract — 2026-10-28 (phase 1)

Deliverable: `cvgen validate --content <dir> [--locale <code>]` checks `<dir>/cv.yaml` against the content schema,
rejects personal data, and reports missing translations, each finding as `file:line: rule: message`.

Acceptance predicates:
- [ ] `uv run cvgen validate --content examples/content` exits 0; so do `--locale en` and `--locale da`.
- [ ] Each forbidden `basics` key (name, email, phone, url, image, location, profiles) exits 1 with rule `pii/key` and the key's line.
- [ ] An email, an international phone number, an 8-digit Danish phone number, a CPR-like number and a LinkedIn profile URL anywhere in the content each exit 1 with the right `pii/*` rule and line, and the offending value is not printed.
- [ ] A work entry without `startDate` exits 1 with rule `schema/required` and the entry's line.
- [ ] `--locale da` with one Danish string removed exits 1 with rule `i18n/missing` and that string's line.
- [ ] A project whose `x-employer` names no work `id` exits 1 with rule `ref/employer`.
- [ ] YAML 1.2 scalars: `no` stays the string `"no"`, `2024-03-01` stays a string; a duplicate key exits 1 with rule `yaml/duplicate-key`.
- [ ] `uv run pytest` and `uv run ruff check . && uv run ruff format --check .` are green.

Runtime path: `uv run cvgen validate --content <dir> [--locale <code>]`, driven by `tests/test_validate.py`.
PII test cases are generated inside the tests (synthetic values), not committed as fixture files, so the repo's own
PII scan never has to allowlist them.

Out of scope this sprint:
- `build`, the runtime PII prompt and `pii.fields.yaml` (phase 2).
- Profile, theme and locale schemas (phases 3–4).

## Next
- Phase 2: runtime PII prompt, language resolution, JSON Resume and JSON-LD export.

## Open issues
- Owner to make the repo private before phase 5 (content import).
