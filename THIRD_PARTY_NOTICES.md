# Third-party notices

Agent skills and harness files under `.claude/`, `docs/checklists/`, `AGENTS.md` and `run.sh` were copied
(some lightly adapted) from these MIT-licensed repositories. Each is used under its MIT license.

| Source | Commit | Copied | License |
|---|---|---|---|
| [bendfeldt/loopkit](https://github.com/bendfeldt/loopkit) (fork of Archive228/loopkit) | `26f8fb9` | `.claude/agents`, `.claude/commands`, `.claude/hooks`, `run.sh`, `AGENTS.md` (adapted), `docs/checklists/`, skills: using-loopkit, spec-first, planner-spec-expand, sprint-contract, feature-list-json, progress-reading-protocol, shift-notes, adversarial-verify, verification-before-completion, self-eval-bias, broken-window-check, write-failing-test-first, contract-test, input-validation, secret-scan, structured-output, pdf-ingestion, design-system, a11y-pass, clean-commits, readme-audit, dependency-audit | MIT, © 2026 Archive228 |
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | `09c434a` | skills: ponytail, ponytail-review, ponytail-audit | MIT, © 2026 DietrichGebert |
| [bendfeldt/Project-Mindflayer](https://github.com/bendfeldt/Project-Mindflayer) | `473572a` | skills: adr, smart-commit, smart-pr, engineering-auditor | MIT, © 2026 bendfeldt |
| [bendfeldt/ECC](https://github.com/bendfeldt/ECC) (fork of everything-claude-code) | `ed38744` | skills: accessibility, browser-qa | MIT, © 2026 Affaan Mustafa |

Adaptations: `using-loopkit` routes ADRs to `adr` instead of `decision-record`; `AGENTS.md` adds the project's privacy rules;
`.claude/settings.json` and `.claude/CLAUDE.md` are rewritten for this project.
