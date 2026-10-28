# cv-generator: plan

Status: **draft for review** (v1, 2026-10-28). Nothing is implemented yet.
How this was made: loopkit `planner-spec-expand` → `spec-first` → `feature-list-json`, then read through ponytail
(smallest thing that fully does the job). Similar projects: `docs/RESEARCH.md`.

## 1. Brief

A command-line tool that builds a CV from YAML files. **Content**, **look**, **language** and **audience** are each
configured in their own file, and the tool only combines them. Data follows open standards (JSON Resume, JSON Schema,
schema.org, ISO/BCP 47 codes, PDF/UA). **No contact detail or other personal data is ever stored in the repository.** The
tool asks for it at runtime and writes it only into the generated files. It is built first for one user (a three-page
Danish/English CV) but uses nothing specific to that user.

## 2. Design language (default theme `sidebar`)

Rebuilds the look of the owner's current CV, with the colors and fonts as tokens in `theme.yaml`:
- **Tone**: calm, professional, two columns. A colored sidebar (accent `#D9984F`) holds photo, details, links, skills,
  languages, interests and education. The main column holds profile, narrative sections, certifications, work and projects.
- **Type**: one sans family (OFL-licensed, embedded). Name large, title below it with a thin rule.
- **Density**: airy main column, compact sidebar. A4, 3 pages at most for the full profile.
- **Skill level**: a bar as decoration, plus a text label for screen readers and ATS.

## 3. Standards used

| Area | Standard | Use |
|---|---|---|
| Content model | [JSON Resume 1.0.0](https://jsonresume.org/schema) | Canonical structure: `basics`, `work`, `projects`, `education`, `certificates`, `skills`, `languages`, `interests`. Extensions use `x-` keys. |
| File format | YAML 1.2 | Every authored file. |
| Validation | JSON Schema 2020-12 | One schema per file kind. Editors get autocompletion through the `yaml-language-server` modeline. |
| Semantic output | schema.org (`Person`, `OrganizationRole`, `EducationalOccupationalCredential`, `DefinedTerm`) as JSON-LD 1.1 | Embedded in the HTML and written as a separate `.jsonld` file. |
| Dates | ISO 8601 (`YYYY-MM` or `YYYY-MM-DD`) | No free-text dates in content. Display format comes from the locale. |
| Locales | BCP 47 (`en`, `da`) | Labels and month names. |
| Countries | ISO 3166-1 alpha-2 | Location (supplied at runtime). |
| Language skill | CEFR (A1–C2) plus `native` | `languages[].fluency`. |
| Skill taxonomy | ESCO URI (optional) | `skills[].x-esco`, so a skill such as "data modelling" means one thing. |
| Phone / email / URL | E.164 / RFC 5322 / RFC 3986 | Validation of the runtime PII prompt. |
| Layout | HTML5 + W3C CSS Paged Media | One template renders both the web page and the PDF. |
| PDF | ISO 32000, PDF/UA-1 (tagged, accessible), XMP metadata | Title, author and keywords filled from runtime values, nothing hardcoded. |
| Accessibility | WCAG 2.2 AA | HTML output; contrast checked for the theme tokens. |
| Versioning | SemVer `schemaVersion` in every file; Conventional Commits; Keep a Changelog | |

## 4. Architecture

```
 content/*.yaml ─┐                         ┌─ out/<name>.pdf      (PDF/UA)
 profile.yaml ───┤                         ├─ out/<name>.html     (+ JSON-LD)
 theme.yaml ─────┼─▶ validate ─▶ resolve ──┼─▶ render ─────────────┤
 locale.yaml ────┘   (schema +   (profile  │                       ├─ out/<name>.json     (JSON Resume)
                      PII guard)  filters) │                       ├─ out/<name>.jsonld   (schema.org)
 pii.fields.yaml ──▶ runtime prompt ───────┘                       ├─ out/<name>.md
   (declares fields,  (values in memory                            └─ out/<name>.txt      (ATS plain text)
    never values)      only)
```

1. **Load** the four kinds of YAML file. Content may live outside the repo (`--content <dir>`).
2. **Validate** each file against its schema. The **PII guard** runs on content:
   - the content schema forbids `basics.name/email/phone/url/location/profiles/image`;
   - a pattern scan of every string rejects email addresses, phone numbers, CPR-like numbers and URLs to personal
     profiles. Errors give file, line and the rule broken.
3. **Prompt for PII**, driven by `pii.fields.yaml` and the profile's `pii.required/optional` lists. Each answer is
   validated (E.164, email, URI, image file type). Non-interactive runs can read `CVGEN_PII_<FIELD>` env vars. Values
   are never logged, cached or written anywhere except the outputs.
4. **Resolve** the profile: pick sections, map them to theme regions (`sidebar`, `main`), filter by tags, date window and
   max counts, order by date or `x-priority`, and fill computed values (e.g. `{years_experience}` from work dates, so
   "over 8 years" never goes stale).
5. **Normalize** to one canonical document: JSON Resume with runtime PII merged in. Everything after this reads only the
   canonical document.
6. **Render**: Jinja2 → HTML → WeasyPrint → PDF (PDF/UA-1). The JSON Resume, JSON-LD, Markdown and text outputs are
   serialisations of the same document.

**Stack** (ponytail: every dependency must replace a lot of code): Python 3.12, `uv`, `PyYAML`, `jsonschema`, `Jinja2`,
`WeasyPrint`; `argparse` for the CLI; `pytest`, `ruff`. Why Python: it is the owner's daily language, and WeasyPrint is the
strongest open CSS Paged Media engine that outputs PDF/UA. Typst would also work (RenderCV uses it), but it is not a
W3C standard and the web output would need a second template.

### Repo layout

```
cv-generator/
├── src/cvgen/            cli.py, load.py, validate.py (schema + PII guard), pii.py (prompt),
│                         resolve.py (profiles), export.py (json, jsonld, md, txt), render.py (html, pdf)
├── schemas/              content | profile | theme | locale | pii-fields  .schema.json
├── pii.fields.yaml       declares PII fields: prompt text, format, target path (no values)
├── profiles/             full-en.yaml, full-da.yaml, architect-short-en.yaml
├── themes/sidebar/       theme.yaml (tokens), cv.html.j2, cv.css, fonts/
├── locales/              en.yaml, da.yaml
├── examples/content/     synthetic CV (fictional person), used by tests and CI
├── tests/
├── docs/                 PLAN.md, RESEARCH.md, adr/
└── .claude/              loopkit harness + skills (see THIRD_PARTY_NOTICES.md)
```

### Example files (shapes, synthetic values)

`content/cv.yaml`: JSON Resume minus every PII field, plus `x-` extensions:

```yaml
# yaml-language-server: $schema=../schemas/content.schema.json
schemaVersion: 1
basics:
  label: Senior Data Architect
  summary: >-
    Data architect with over {years_experience} years of experience ...
x-narrative:                  # free sections the standard lacks ("The Architectural Approach" ...)
  - id: approach
    title: { en: "The Architectural Approach: Holistic & Objective", da: "..." }
    body: { en: "...", da: "..." }
    bullets: [ { term: Platform Leadership, text: "..." } ]
work:
  - id: acme
    name: Acme Data A/S
    position: Solution Lead
    location: Copenhagen
    startDate: 2024-03
    summary: "..."
    x-tags: [architecture, leadership]
projects:
  - name: Example Client
    x-employer: acme            # links a client project to the work entry it was done under
    startDate: 2025-06
    highlights:
      - { text: "Architected a **Lakehouse-based** platform ...", x-priority: 1, x-tags: [architecture] }
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
  formats: [pdf, html, json, jsonld, md, txt]
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

## 5. Privacy design

| Risk | Control |
|---|---|
| PII committed in content | Content schema forbids PII keys; the pattern scan fails `validate` and `build`; the same scan runs in a pre-commit hook and in CI. |
| PII in generated files committed | `out/`, `*.pdf` and images are gitignored; CI fails if a tracked file matches. |
| Photo committed | Never in the repo. Path given at runtime; embedded in memory as a data URI. |
| PII leaking through logs or tracebacks | PII values are wrapped in a type whose `repr` is `***`; no logging of resolved documents. |
| PII in PDF metadata | Set only from runtime values. Nothing is defaulted from the environment or git config. |
| Agents reading real data | `.claude/settings.json` denies `Read` on `private/**` and `out/**`; AGENTS.md rules. |
| Tests needing PII | Synthetic fixtures (`example.com`, clearly fake numbers), generated inside the test. |
| **Career history is personal data too** (GDPR), even without a name, and this repo is **public** | **Decision needed, see §7.1.** Recommendation: real content lives in a separate **private** repo or folder, passed with `--content`. This repo keeps only the engine and the synthetic example. |

## 6. Phases (each is one sprint with a signed `sprint-contract`)

| Phase | Deliverable | Done when (script-decidable) | Main skills |
|---|---|---|---|
| **0** | Harness, skills, plan, research *(this commit)* | Files present; `secret-scan` clean | spec-first, planner-spec-expand, feature-list-json |
| **1** | Schemas + synthetic example + `cvgen validate` with PII guard | `uv run cvgen validate --content examples/content` exits 0; each planted PII fixture in `tests/fixtures/pii/` exits 1 with file:line | write-failing-test-first, input-validation, contract-test, structured-output |
| **2** | Runtime PII prompt + JSON Resume + JSON-LD export | Built `.json` passes the official JSON Resume schema; `.jsonld` parses as schema.org `Person`; a test proves no PII value appears outside `out/` | input-validation, secret-scan, contract-test |
| **3** | `sidebar` theme, HTML + PDF | The PDF of the example builds; text extraction contains every section heading in order; Playwright screenshot diff under threshold | design-system, browser-qa, a11y-pass |
| **4** | Profiles + `en`/`da` locales + localized strings | `full-en`, `full-da` and `architect-short-en` all build; the short profile has fewer projects and ≤ 2 pages | sprint-contract, broken-window-check |
| **5** | Import of your current CV into **private** content | `cvgen validate --content <private dir>` exits 0; a build visually matches the current PDF | pdf-ingestion (run locally, nothing committed) |
| **6** | Quality outputs: Markdown, ATS text, PDF/UA tags, page-budget trimming | veraPDF reports PDF/UA-1 pass; ATS round trip (text extraction) shows dates and titles per entry | accessibility, verification-before-completion |
| **7** | CI: lint, tests, validate + build on synthetic data, PII scan | GitHub Actions green on a PR; a planted PII commit is rejected | dependency-audit, secret-scan, smart-pr |

Every phase ends with `/verify` (loopkit adversarial verifier) and a `ponytail-review` of the diff. `ponytail-audit` and
`engineering-auditor` run once after phase 7.

**Out of scope for v1:** GUI editor, DOCX output, cover letters, Europass/HR-Open export, AI tailoring to a job ad.
**Later candidate:** job-description tailoring that only re-ranks and selects existing highlights, plus a fact-check gate
that fails if output text is not in the content (the career-ops idea).

## 7. Open decisions

1. **Where does the real content live?** (a) separate private repo `cv-content`, passed with `--content` *(recommended)*;
   (b) gitignored `private/` folder in this repo, local only; (c) committed here (public: not recommended).
2. **Should the repo stay public?** It can: the engine has no personal data if 7.1 is (a) or (b).
3. **Danish and English content**: inline `{en:, da:}` maps in one file *(recommended: no drift between languages)*, or
   one content file per language.
4. **PDF engine**: WeasyPrint (HTML/CSS, W3C) *(recommended)* or Typst.
