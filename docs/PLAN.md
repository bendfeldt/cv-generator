# cv-generator: plan

Status: **accepted, v2** (2026-10-28). Nothing is implemented yet. Decisions: §7.
How this was made: loopkit `planner-spec-expand` → `spec-first` → `feature-list-json`, then read through ponytail
(smallest thing that fully does the job). Similar projects: `docs/RESEARCH.md`.

## 1. Brief

A command-line tool that builds a CV from YAML files. **Content**, **look**, **language** and **audience** are each
configured in their own file, and the tool only combines them. Data follows open standards (JSON Resume, JSON Schema,
schema.org, ISO/BCP 47 codes, tagged PDF/UA). Danish and English text live side by side in the same content file.
**No contact detail or other personal data is ever stored in the repository.** The tool asks for it at runtime and
writes it only into the generated files. PDF is typeset with LaTeX (LuaLaTeX). It is built first for one user (a
three-page Danish/English CV) but uses nothing specific to that user.

## 2. Design language (default theme `sidebar`)

Rebuilds the look of the owner's current CV, with the colors and fonts as tokens in `theme.yaml`:
- **Tone**: calm, professional, two columns. A colored sidebar (accent `#D9984F`) holds photo, details, links, skills,
  languages, interests and education. The main column holds profile, narrative sections, certifications, work and projects.
- **Type**: one sans family (OFL-licensed, loaded with `fontspec`). Name large, title below it with a thin rule.
- **Density**: airy main column, compact sidebar. A4, 3 pages at most for the full profile.
- **Skill level**: a bar as decoration (TikZ), plus a text label in the tagged PDF and the text outputs.

## 3. Standards used

| Area | Standard | Use |
|---|---|---|
| Content model | [JSON Resume 1.0.0](https://jsonresume.org/schema) | Canonical structure: `basics`, `work`, `projects`, `education`, `certificates`, `skills`, `languages`, `interests`. Extensions use `x-` keys. |
| File format | YAML 1.2 | Every authored file. |
| Validation | JSON Schema 2020-12 | One schema per file kind. Editors get autocompletion through the `yaml-language-server` modeline. |
| Semantic output | schema.org (`Person`, `OrganizationRole`, `EducationalOccupationalCredential`, `DefinedTerm`) as JSON-LD 1.1 | Written as a `.jsonld` file. |
| Dates | ISO 8601 (`YYYY-MM` or `YYYY-MM-DD`) | No free-text dates in content. Display format comes from the locale. |
| Locales | BCP 47 (`en`, `da`) | Keys of localized strings, labels, month names, `babel` language. |
| Countries | ISO 3166-1 alpha-2 | Location (supplied at runtime). |
| Language skill | CEFR (A1–C2) plus `native` | `languages[].fluency`. |
| Skill taxonomy | ESCO URI (optional) | `skills[].x-esco`, so a skill such as "data modelling" means one thing. |
| Phone / email / URL | E.164 / RFC 5322 / RFC 3986 | Validation of the runtime PII prompt. |
| Typesetting | LaTeX (LuaLaTeX, TeX Live 2025+), built with `latexmk` | The most used CV toolchain (Awesome-CV, moderncv). LuaLaTeX is the LaTeX Project's recommended engine for new documents and the one its tagging code targets. |
| PDF | ISO 32000; PDF/UA-2 via `\DocumentMetadata{tagging=on, pdfstandard=ua-2, lang=…}`; XMP metadata | Tagged, accessible PDF. Title, author and keywords filled from runtime values, nothing hardcoded. |
| Versioning | SemVer `schemaVersion` in every file; Conventional Commits; Keep a Changelog | |

## 4. Architecture

```
 content/*.yaml ─┐                         ┌─ out/<name>.pdf      (LuaLaTeX, PDF/UA-2)
 profile.yaml ───┤                         ├─ out/<name>.json     (JSON Resume)
 theme/ ─────────┼─▶ validate ─▶ resolve ──┼─▶ render ───────────┤
 locale.yaml ────┘   (schema +   (profile, │                     ├─ out/<name>.jsonld   (schema.org)
                      PII guard)  language)│                     ├─ out/<name>.md
 pii.fields.yaml ──▶ runtime prompt ───────┘                     └─ out/<name>.txt      (ATS plain text)
   (declares fields,  (values in memory
    never values)      only)
```

1. **Load** the four kinds of YAML file.
2. **Validate** each file against its schema. The **PII guard** runs on content:
   - the content schema forbids `basics.name/email/phone/url/location/profiles/image`;
   - a pattern scan of every string rejects email addresses, phone numbers, CPR-like numbers and URLs to personal
     profiles. Errors give file, line and the rule broken.
   - `validate --locale da` also lists every localized string missing a Danish value.
3. **Prompt for PII**, driven by `pii.fields.yaml` and the profile's `pii.required/optional` lists. Each answer is
   validated (E.164, email, URI, image file type). Non-interactive runs can read `CVGEN_PII_<FIELD>` env vars. Values
   are never logged, cached or written anywhere except the outputs.
4. **Resolve** the profile:
   - **language**: every localized string `{en: …, da: …}` becomes the profile's locale, falling back to
     `fallbackLocale`; a plain string is used as-is in every language (names, tools, codes);
   - pick sections, map them to theme regions (`sidebar`, `main`), filter by tags, date window and max counts, order by
     date or `x-priority`;
   - fill computed values (e.g. `{years_experience}` from work dates, so "over 8 years" never goes stale).
5. **Normalize** to one canonical document: JSON Resume in one language, with runtime PII merged in. Everything after
   this reads only the canonical document.
6. **Render**:
   - **PDF**: Jinja2 fills `cv.tex.j2` (with LaTeX-safe delimiters `\VAR{}` / `\BLOCK{}`). Every value passes an escape
     filter for LaTeX special characters (`\ { } $ & # ^ _ ~ %`); `**bold**` in content becomes `\textbf{}`. The `.tex`
     is written to a temporary directory, compiled with `latexmk -lualatex -no-shell-escape`, the PDF is copied to `out/`,
     and the temporary directory (holding the `.tex`, the logs and a photo copy, all with PII) is deleted.
   - **JSON Resume, JSON-LD, Markdown, text** are serialisations of the same document. Any JSON Resume theme can turn
     the `.json` into a web page, so no HTML theme is built in v1.

**Stack** (ponytail: every dependency must replace a lot of code): Python 3.12, `uv`, `PyYAML`, `jsonschema`, `Jinja2`;
`argparse` for the CLI; `pytest`, `ruff`. System: TeX Live 2025+ (`lualatex`, `latexmk`, packages `fontspec`, `babel`,
`paracol`, `tikz`, `hyperref`), and `poppler-utils` for tests (`pdftotext`, `pdftoppm`).

### Repo layout

```
cv-generator/
├── src/cvgen/            cli.py, load.py, validate.py (schema + PII guard), pii.py (prompt),
│                         resolve.py (profiles, language), export.py (json, jsonld, md, txt), latex.py (escape, compile)
├── schemas/              content | profile | theme | locale | pii-fields  .schema.json
├── pii.fields.yaml       declares PII fields: prompt text, format, target path (no values)
├── content/              the owner's real CV content (no PII); added only once the repo is private, see §5
├── profiles/             full-en.yaml, full-da.yaml, architect-short-en.yaml
├── themes/sidebar/       theme.yaml (tokens), cv.tex.j2, fonts/
├── locales/              en.yaml, da.yaml (labels, month names, babel language)
├── examples/content/     synthetic CV (fictional person), used by tests and CI
├── tests/
├── docs/                 PLAN.md, RESEARCH.md
└── .claude/              loopkit harness + skills (see THIRD_PARTY_NOTICES.md)
```

### Example files (shapes, synthetic values)

`content/cv.yaml`: JSON Resume minus every PII field, plus `x-` extensions. Text that differs per language is a map;
text that is the same in both stays a plain string:

```yaml
# yaml-language-server: $schema=../schemas/content.schema.json
schemaVersion: 1
basics:
  label: { en: Senior Data Architect, da: Senior dataarkitekt }
  summary:
    en: Data architect with over {years_experience} years of experience ...
    da: Dataarkitekt med over {years_experience} års erfaring ...
x-narrative:                  # free sections the standard lacks ("The Architectural Approach" ...)
  - id: approach
    title: { en: "The Architectural Approach: Holistic & Objective", da: "..." }
    body: { en: "...", da: "..." }
    bullets: [ { term: { en: Platform Leadership, da: Platformledelse }, text: { en: "...", da: "..." } } ]
work:
  - id: acme
    name: Acme Data A/S
    position: { en: Solution Lead, da: Solution Lead }
    location: Copenhagen
    startDate: 2024-03
    summary: { en: "...", da: "..." }
    x-tags: [architecture, leadership]
projects:
  - name: Example Client
    x-employer: acme            # links a client project to the work entry it was done under
    startDate: 2025-06
    highlights:
      - text: { en: "Architected a **Lakehouse-based** platform ...", da: "..." }
        x-priority: 1
        x-tags: [architecture]
skills:
  - { name: Data Modelling, level: "5", x-scale: 1-5, x-esco: "http://data.europa.eu/esco/skill/..." }
languages:
  - { language: da, fluency: native }
  - { language: en, fluency: C2 }
certificates:
  - { name: Fabric Analytics Engineer Associate, issuer: Microsoft, x-code: DP-600 }
```

`profiles/full-en.yaml`:

```yaml
schemaVersion: 1
id: full-en
locale: en
fallbackLocale: en
theme: sidebar
regions:
  sidebar: [photo, contact, links, skills, languages, interests, education]
  main:    [summary, narrative, certificates, work, projects]
filters:
  projects: { since: 2018-01, max: 10, order: startDate-desc }
  highlights: { maxPerEntry: 4, includeTags: [] }
pii:
  required: [name, email, phone, city, country]
  optional: [linkedin, photo]
output:
  formats: [pdf, json, jsonld, md, txt]
  filename: "cv-{profile}-{date}"
  pageLimit: 3
```

`pii.fields.yaml` (declarations only):

```yaml
schemaVersion: 1
fields:
  name:     { prompt: "Full name",              format: text,  target: basics.name }
  email:    { prompt: "Email",                  format: email, target: basics.email }
  phone:    { prompt: "Phone (E.164, +45...)",  format: e164,  target: basics.phone }
  city:     { prompt: "City",                   format: text,  target: basics.location.city }
  country:  { prompt: "Country (ISO 3166)",     format: iso3166-alpha2, target: basics.location.countryCode }
  linkedin: { prompt: "LinkedIn URL",           format: uri,   target: "basics.profiles[network=LinkedIn].url" }
  photo:    { prompt: "Path to photo",          format: image-file, target: basics.image }
```

## 5. Privacy and repo safety

The repo will be made **private**, so the owner's career content (no PII) lives in `content/`. Contact details and the
photo stay runtime-only regardless. On GitHub Free, a private repo cannot enforce branch protection on `main`; the
controls below make up for that.

| Risk | Control |
|---|---|
| PII committed in content | Content schema forbids PII keys; the pattern scan fails `validate` and `build`; the same scan runs in a pre-commit hook and in CI. |
| Career content committed while the repo is still public | `content/` is added only after the repo is private. A CI job fails if `content/` exists and `github.event.repository.private` is false, so making the repo public again is caught on the next run. |
| PII in generated files committed | `out/`, `*.pdf`, `*.tex` outside `themes/`, and images are gitignored; CI fails if a tracked file matches. |
| PII left on disk by LaTeX | Compilation runs in a temporary directory that is deleted after the build, also on failure. |
| Photo committed | Never in the repo. Path given at runtime; copied only into the temporary build directory. |
| LaTeX injection from content or prompt (`\input`, `\write18`) | Every value is escaped; `latexmk` runs with `-no-shell-escape`. A test feeds `\input{/etc/passwd}` and `\write18{…}` and checks they print literally. |
| PII leaking through logs or tracebacks | PII values are wrapped in a type whose `repr` is `***`; LaTeX logs stay in the deleted temp dir; no logging of resolved documents. |
| PII in PDF metadata | Set only from runtime values. Nothing is defaulted from the environment or git config. |
| No branch protection on `main` (private repo, Free plan) | Tracked `.githooks/pre-push` refuses pushes to `main` (enable with `git config core.hooksPath .githooks`); work goes through PRs with CI; AGENTS.md forbids agents pushing to `main`. GitHub Pro would restore enforced protection. |
| Agents reading generated CVs | `.claude/settings.json` denies `Read` on `out/**`; AGENTS.md rules. |
| Tests needing PII | Synthetic fixtures (`example.com`, clearly fake numbers), generated inside the test. |

## 6. Phases (each is one sprint with a signed `sprint-contract`)

| Phase | Deliverable | Done when (script-decidable) | Main skills |
|---|---|---|---|
| **0** | Harness, skills, plan, research *(done)* | Files present; `secret-scan` clean | spec-first, planner-spec-expand, feature-list-json |
| **1** | Schemas + synthetic example + `cvgen validate` with PII guard and missing-translation report | `uv run cvgen validate --content examples/content` exits 0; each PII case generated in `tests/test_validate.py` exits 1 with file:line; `--locale da` on an example missing one Danish string exits 1 naming it | write-failing-test-first, input-validation, contract-test, structured-output |
| **2** | Runtime PII prompt + language resolution + JSON Resume + JSON-LD export | Built `.json` passes the official JSON Resume schema; `.jsonld` parses as schema.org `Person`; the `da` build has no English localized strings; a test proves no PII value appears outside `out/` | input-validation, secret-scan, contract-test |
| **3** | `sidebar` LaTeX theme → PDF | The example PDF builds with `latexmk -lualatex`; `pdftotext` shows every section heading in order; `pdftoppm` render matches the reference image within a threshold; the temp dir is gone after the build; injection test passes | design-system, input-validation |
| **4** | Profiles + `en`/`da` locales | `full-en`, `full-da` and `architect-short-en` all build; Danish build has Danish headings and month names (`babel`); the short profile has fewer projects and ≤ 2 pages | sprint-contract, broken-window-check |
| **5** | Import of the current CV into `content/` (**after the repo is private**) | Repo is private; `cvgen validate --content content --locale da` and `--locale en` exit 0; the `full-en` build visually matches the current PDF | pdf-ingestion |
| **6** | Quality outputs: Markdown, ATS text, PDF/UA-2 tagging, page-budget trimming | veraPDF reports PDF/UA-2 pass (risk: `paracol`/TikZ tagging support is still maturing; fallback is a single-column flow for the tagged build); `pdftotext` round trip shows title and dates per entry in reading order | accessibility, verification-before-completion |
| **7** | CI + repo guards | GitHub Actions (TeX Live 2025 image) green on a PR; a planted PII commit is rejected; the public-repo guard fails on a public fork; `.githooks/pre-push` refuses `main` | dependency-audit, secret-scan, smart-pr |

Every phase ends with `/verify` (loopkit adversarial verifier) and a `ponytail-review` of the diff. `ponytail-audit` and
`engineering-auditor` run once after phase 7.

**Out of scope for v1:** built-in HTML theme (use any JSON Resume theme on the `.json`), GUI editor, DOCX output, cover
letters, Europass/HR-Open export, AI tailoring to a job ad.
**Later candidate:** job-description tailoring that only re-ranks and selects existing highlights, plus a fact-check gate
that fails if output text is not in the content (the career-ops idea).

## 7. Decisions

| # | Question | Decision (2026-10-28) |
|---|---|---|
| 1 | Where does the real content live? | In this repo under `content/`, **once the repo is private**. PII and the photo stay runtime-only. |
| 2 | Public or private repo? | Private. Branch protection is lost on the Free plan; compensated as in §5. |
| 3 | Danish and English content | Side by side: localized strings as `{en: …, da: …}` maps in one file; plain strings for text that is the same in both. |
| 4 | PDF engine | LaTeX, the most used CV toolchain and one the owner already knows. Engine: LuaLaTeX (LaTeX Project's recommended engine, and needed for PDF/UA tagging). |
| 5 | HTML output | Dropped from v1. Any JSON Resume theme renders the exported `.json` as a web page. |
