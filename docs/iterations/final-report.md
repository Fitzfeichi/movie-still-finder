# Final report — still-finder 1.0.0

[中文版 / Chinese version](final-report.zh-CN.md)

**Date:** 2026-11-06
**Standard used:** "a well-regarded open-source GitHub project" — self-contained,
reproducible, honest about limits, pleasant for a stranger to start with.
**Rounds completed:** 3 (plus a separate live-network verification task).

## What was generalised

The starting point was a project-private skill that only worked on one machine:
it pointed at private rule files and ledgers, hard-coded a Windows Python
interpreter and font paths, depended on logged-in CLIs, and kept its scripts in
a research folder. The result is a standalone repo with no credentials, no
machine paths and no copyrighted assets.

| Round | Focus | Result |
|---|---|---|
| 1 | Skeleton + static gate | 2 placeholder failures + 4 manual consistency findings, all fixed; static gate PASS |
| 2 | Portable CLI + offline e2e + live check | 30 offline checks PASS; 1 real code defect (Referer) fixed; 3 live commands verified; scanner false positive fixed |
| 3 | Stranger's-eye review | 8 findings fixed (stale examples, unrunnable meme command, Pillow warning, misleading output, undocumented warnings); full regression PASS; git init verified |

## Deliverables

```
still-finder/
  SKILL.md                 Agent Skills entry point (progressive disclosure)
  README.md / README.zh-CN.md   English + full Chinese documentation
  LICENSE / CONTRIBUTING.md / CHANGELOG.md / .gitignore / requirements.txt
  .github/workflows/ci.yml      Python 3.9/3.11/3.12, fully offline
  scripts/still.py              11-command portable CLI
  scripts/still_lib.py          fetch / extract / validate / sheet / images / deliver
  references/workflow.md        self-contained end-to-end SOP
  references/sources.md         source priority, headers, dated failures
  references/pitfalls.md        ~33 recorded failure modes
  references/image-ops.md       contact sheet, cropping, subtitles, fonts
  references/fact-check.md      two real misattribution cases
  references/delivery.md        provenance schema, dual folders, copyright
  references/meme-optional.md   optional 梗图 appendix
  references/optional-adapters.md  local-video / login-based add-ons
  profiles/minimal.json         default, general-purpose
  profiles/editorial-wechat.json  opt-in human editor workflow
  profiles/README.md            schema + hard rules
  examples/                     quickstart, sample request, sample picks
  tests/                        synthetic fixtures, offline e2e, portability gate
  docs/iterations/              round-1/2/3 reports + this file
```

## Quality gates (all passing)

| Gate | Result |
|---|---|
| Offline end-to-end on synthetic `file://` fixtures | 30 checks PASS |
| Portability / privacy / no-deletion / link / frontmatter scan | PASS in `--full` mode |
| Python byte compile, 11/11 subcommand `--help`, JSON validity | PASS |
| Both profiles load; hard-rule disabling is rejected | PASS |
| Live `probe` | 6/7 hosts reachable |
| Live `quote` / `full` / `grab` | SUCCESS (timestamps, 1920x1080 frame, 23 candidates) |
| Copy-paste README run from a clean external directory | SUCCESS |
| No image assets, no credentials, no machine paths in the repo | PASS |
| `git init` + ignore-rule verification | 15 top-level entries, zero images |

## Against the "high-quality GitHub project" bar

**Met:** clear one-line purpose; install in three lines; a 60-second example
that actually runs; honest statement of what is impossible; bilingual docs;
MIT licence; changelog; contributing guide with a dated source-reporting
workflow; CI; automated offline tests; a permanent privacy/portability gate;
dated, evidence-based field notes; explicit copyright and anti-bypass policy;
no fabricated URLs, badges or stars.

**Not met / deliberately out of scope:** no real GitHub push (needs
authorisation and a repository URL); CI has not executed on GitHub itself;
Python 3.9/3.11/3.12 matrix unverified locally; `frames` not live-verified;
no issue templates or release automation. These are listed rather than hidden.

## Design decisions worth remembering

- **Credentials are a bug.** Anything needing a login, signature or paid plan
  is an optional adapter, never a dependency.
- **Profiles can only tighten.** Provenance, subtitle labelling, dead-end
  logging and no-deletion are code-level rules. A profile that disables them is
  rejected. The editor's personal preferences live in one opt-in JSON file, so
  someone who wants "results like the original author" can enable them with a
  single flag.
- **Vision picking is mandatory.** A live run produced 23 valid images of which
  most were title cards; hit count is not semantic match.
- **Record dead ends with dates.** Source availability drifted within this very
  session; the field notes are the accumulated memory.
- **No real stills ship with the code.** Test images are generated at runtime.

## What was deliberately NOT done

- No `git commit`, no remote, no push, no publish.
- No login performed on the user's behalf, no credential stored or requested.
- No real film stills copied into the repository.
- No existing project file was modified. The original private skill, SOPs,
  ledgers and research folders remain exactly as they were.
- No automation or scheduled task was created.

## If you want to publish

1. Rename the folder / choose a repository name and confirm the LICENSE holder.
2. Add the repository URL as the `origin` remote, then stage and commit
   (`git add -A && git commit -m "Initial release"`).
3. `git push`. CI runs offline only; it never needs a key.
4. For a 5-minute demo, follow `examples/quickstart.md` section A (live) or D
   (fully offline). Enable the editor workflow with
   `python scripts/still.py rules --profile profiles/editorial-wechat.json`.
