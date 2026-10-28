# cv-generator

Build a CV from YAML: content, look, language and audience each live in their own file. Danish and English text live side by
side. Output is a LaTeX-typeset PDF,
[JSON Resume](https://jsonresume.org), schema.org JSON-LD, Markdown and plain text.

**Personal data is never stored.** Name, contact details, links and photo are asked for when you build, and are written
only into the generated files in `out/` (gitignored).

Status: planning. See [docs/PLAN.md](docs/PLAN.md) for the design and [docs/RESEARCH.md](docs/RESEARCH.md) for how
this compares to similar projects.

Agent harness and skills: loopkit, ponytail and others, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
