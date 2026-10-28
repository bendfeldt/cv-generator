# Similar projects: conceptual analysis

Scope: what these projects do and how they are designed, not which language they use.
GitHub stars are as of 2026-10-28.

## 1. The projects

| # | Project | ★ | Core idea |
|---|---|---|---|
| 1 | [jsonresume](https://github.com/jsonresume) (schema, resume-cli, themes) | 4.7k (cli) | An open, community-owned **schema** for résumé data. Themes are separate packages that render the same document. |
| 2 | [HackMyResume](https://github.com/hacksalot/HackMyResume) / FRESH | 9.3k | One source, **many formats** (HTML, MD, LaTeX, DOCX, PDF, TXT). Converts between two schemas (JSON Resume ⇄ FRESH). |
| 3 | [RenderCV](https://github.com/rendercv/rendercv) | 17.8k | One YAML file split into **`cv` / `design` / `locale` / `settings`**. Strict validation against a published JSON Schema, which gives editor autocompletion and errors that point to the exact line. Pluggable themes. Ships an AI agent skill. |
| 4 | [YAMLResume](https://github.com/yamlresume/yamlresume) | 1.6k | "Resumes as code": a **compiler** model (`validate` gives compiler-style diagnostics). One file declares several **layouts** (outputs) at once. i18n via a `locale` option. Imports JSON Resume. |
| 5 | [brilliant-CV](https://github.com/yunanwg/brilliant-CV) | 0.8k | **Profiles** (one folder per audience or language) picked at compile time. Modular sections. Opt-in ATS keywords, also written to the PDF *Keywords* metadata. |
| 6 | [rac](https://github.com/jamesbiederbeck/rac) | new | A typed **semantic model**: a Person has Positions; **Claims** attach to positions; Competencies and Organizations are shared entities. **Build profiles** filter claims by tag and weight, and can optionally rank them against a job description. Claims have **visibility** (public or private). The PDF can **trim the lowest-priority claims to fit a page limit**. JSON Resume is a lossy export. |
| 7 | [imprecv](https://github.com/jskherman/imprecv) | 0.5k | The minimal version: YAML data and one template, version-controlled. |
| 8 | [Reactive Resume](https://github.com/reactive-resume/reactive-resume) | 45k | A web **GUI** builder, privacy-first and self-hostable. JSON Resume import, many templates, an MCP server. |
| 9 | [OpenResume](https://github.com/xitanggg/open-resume) | 9.0k | Builder plus **résumé parser** running locally in the browser: you can check how an ATS reads your PDF. |
| 10 | [Resume-Matcher](https://github.com/srbhr/Resume-Matcher) | 28.9k | **ATS-style matching** of a CV against a job description: keyword gaps and similarity score. |
| 11 | [career-ops](https://github.com/career-ops-hq/career-ops) | 78k | An agent-driven job search. The CV source of truth is one file. Tailoring per job follows "**reformulate, never fabricate**", backed by a **fact-check gate in code** that blocks a generated CV whose numbers or facts are not in the source. **User data lives outside the code folder** (env var or marker file) and is gitignored. |
| 12 | [Awesome-CV](https://github.com/posquit0/Awesome-CV), modern-cv, chicv | 28.8k | Pure **design templates**. Data is mixed into the template. |
| 13 | "resume-as-code" repos (cv_hub, opariffazman/resume-as-code, …) | small | **CI builds** the CV on push and publishes it to GitHub Pages. |

## 2. Concepts, and whether we adopt them

| Concept | Seen in | Adopt? | How |
|---|---|---|---|
| Open standard schema as the canonical data | 1, 2, 4, 6, 8 | **Yes** | JSON Resume 1.0 is the content model. Our extensions are additive. |
| Data / design / locale / settings separation | 3, 4 | **Yes** | Four kinds of file: content, theme, locale, profile. |
| Published JSON Schema → editor autocomplete + exact errors | 3, 4 | **Yes** | `schemas/*.schema.json` (JSON Schema 2020-12), linked from YAML via `# yaml-language-server: $schema=`. |
| Compiler model: `validate` before `build` | 4 | **Yes** | `cvgen validate` is also the PII guard. |
| Many outputs from one source | 2, 4 | **Yes** | PDF, JSON Resume, JSON-LD, Markdown, plain text. HTML comes from any JSON Resume theme. |
| Pluggable themes | 1, 3, 12 | **Yes** | Theme = LaTeX template + `theme.yaml` design tokens. Exporting JSON Resume also makes any JSON Resume theme usable. |
| Build profiles (audience/language) without copying content | 5, 6 | **Yes** | `profiles/*.yaml` select, order and limit content. |
| Tags, priority and visibility per item | 6 | **Yes** | Optional `x-tags`, `x-priority` and `x-visibility` on entries and highlights. |
| Trim to a page budget by priority | 6 | **Later** (phase 6) | Drop the lowest-priority highlights until the page count fits. |
| Hidden ATS keyword text | 5 | **No** | Hidden text misleads screeners. We use honest PDF Keywords metadata and an accurate plain-text output instead. |
| ATS round-trip check (parse our own PDF) | 9 | **Yes** (test) | Extract text from the built PDF and assert that sections and dates come out in order. |
| Job-description matching / tailoring | 6, 10, 11 | **Later**, optional | Only with a career-ops-style fact-check gate: nothing in the output that is not in the content. |
| User data outside the code folder | 11 | **Partly** | Career content (no PII) lives in `content/` of this repo once it is private; PII and the photo never touch disk outside `out/` and a deleted temp dir. |
| GUI editor | 8 | **No** (out of scope) | YAML + schema + editor autocomplete is the editor. |
| CI build + publish to Pages | 13 | **Partly** | CI validates and builds **synthetic** examples only. Publishing a real CV would need PII in CI, which breaks our core rule. |

## 3. The gap this project fills

Every project above stores contact details in the same file as the content: `basics.email`, a `phone` field, the photo
path. None of them treats personal data as **runtime-only input**. The closest is career-ops, which keeps user data in a
separate gitignored folder, but that data still sits on disk inside the project's reach.

So the differentiators are:

1. **PII by declaration, not by value.** The repo declares which personal fields exist, how to validate them and where
   they go. Values arrive at runtime.
2. **Schema-enforced guard.** The content schema *forbids* PII properties, and a pattern scan rejects emails, phone
   numbers and Danish CPR-like numbers anywhere in the content.
3. **Standards on both ends.** JSON Resume in, and JSON Resume plus schema.org JSON-LD plus tagged, accessible PDF out.
4. **Profiles plus claim-level metadata** (from rac and brilliant-CV) on top of a standard schema rather than a custom one.

## 4. Lessons from failures

- **HackMyResume/FRESH**: a second, competing schema split the ecosystem, and the project has largely stalled. Lesson:
  don't invent a schema. Extend the standard one.
- **Template-only projects (Awesome-CV)**: data and design are mixed, so every change of look means re-typing content.
  Lesson: themes must only read the canonical document.
- **Skill bars** (common in GUI templates and in the current CV): they carry no machine-readable meaning and ATS parsers
  ignore them. Lesson: store a level on a defined scale, render the bar as decoration, and always include a text
  equivalent.
