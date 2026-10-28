STATUS: in-progress

# Implementation plan
Phases and contracts: `docs/PLAN.md` §6. Feature ledger: `feature_list.json`.

## Done
- Phase 0: harness, skills, plan, research.
- Phase 1: content schema, synthetic example, `cvgen validate` with PII guard (ledger: 5 entries pass).
- Decisions recorded in `docs/PLAN.md` §7 (private repo, `{en, da}` strings, LuaLaTeX, no HTML in v1).

## Sprint contract — 2026-10-28 (phase 1)

Deliverable: `cvgen validate --content <dir> [--locale <code>]` checks `<dir>/cv.yaml` against the content schema,
rejects personal data, and reports missing translations, each finding as `file:line: rule: message`.

Acceptance predicates:
- [x] `uv run cvgen validate --content examples/content` exits 0; so do `--locale en` and `--locale da`.
- [x] Each forbidden `basics` key (name, email, phone, url, image, location, profiles) exits 1 with rule `pii/key` and the key's line.
- [x] An email, an international phone number, an 8-digit Danish phone number, a CPR-like number and a LinkedIn profile URL anywhere in the content each exit 1 with the right `pii/*` rule and line, and the offending value is not printed.
- [x] A work entry without `startDate` exits 1 with rule `schema/required` and the entry's line.
- [x] `--locale da` with one Danish string removed exits 1 with rule `i18n/missing` and that string's line.
- [x] A project whose `x-employer` names no work `id` exits 1 with rule `ref/employer`.
- [x] YAML 1.2 scalars: `no` stays the string `"no"`, `2024-03-01` stays a string; a duplicate key exits 1 with rule `yaml/duplicate-key`.
- [x] `uv run pytest` and `uv run ruff check . && uv run ruff format --check .` are green.

Runtime path: `uv run cvgen validate --content <dir> [--locale <code>]`, driven by `tests/test_validate.py`.
PII test cases are generated inside the tests (synthetic values), not committed as fixture files, so the repo's own
PII scan never has to allowlist them.

Out of scope this sprint:
- `build`, the runtime PII prompt and `pii.fields.yaml` (phase 2).
- Profile, theme and locale schemas (phases 3–4).

Result: `/verify` passed on round 8 (rounds 1-7 found PII bypasses, crashes, key leaks and false positives; all fixed
with tests). 96 tests. Decision during the sprint: the phone scan is strict (only dash-separated year ranges are
exempt) and only schema-defined keys are ever printed; see docs/PLAN.md §5.

## Next
- Phase 2: runtime PII prompt, language resolution, JSON Resume and JSON-LD export.
- Ledger entries 1 (scaffold) and 2 (all five schemas) stay open until `build` and the profile/theme/locale/pii-fields
  schemas exist.

## Open issues
- Owner to make the repo private before phase 5 (content import).
