@../AGENTS.md

# Project: cv-generator
Metadata-driven CV generator: YAML content + profile + theme + locale in, PDF (LuaLaTeX)/JSON Resume/JSON-LD/Markdown/text out. Danish and English text side by side.
Contact details and other PII are asked for at runtime and never stored. The plan is `docs/PLAN.md`; research is `docs/RESEARCH.md`.

Stack (planned, see docs/PLAN.md §4): Python 3.12 + uv, PyYAML, jsonschema, Jinja2; TeX Live 2025+ (lualatex, latexmk).
Layout: `src/cvgen/` (code), `schemas/` (JSON Schema), `themes/`, `profiles/`, `locales/`, `content/` (owner's career content, no PII; only once the repo is private), `examples/` (synthetic data only), `tests/`.

## Commands (once phase 1 lands)
- `uv run cvgen validate --content examples/content` — schema + PII guard
- `uv run cvgen build --profile <id> --content <dir>` — prompts for PII, writes to `out/`
- `uv run pytest` — tests
- `uv run ruff check . && uv run ruff format --check .` — lint/format

## Conventions
- Match the existing code in the file you're editing. Read it before you write.
- One change, one purpose. No "while I was in there".
- Default coding posture: the `ponytail` skill (smallest complete change). Review with `ponytail-review`, audit with `ponytail-audit`.

## Claude-specific
- Slash commands live in `.claude/commands/`. `/spec` and `/verify` are the primary entry points.
- The `verifier` subagent (`.claude/agents/verifier.md`) is dispatched by `/verify`.
- Never read `out/`: generated CVs contain the owner's PII.
- Never add or change `content/` while the repo is public.
