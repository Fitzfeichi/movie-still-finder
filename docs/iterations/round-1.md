# Round 1 — skeleton and static self-check

**Date:** 2026-11-06
**Goal:** Turn the private, single-machine workflow into a self-contained repo
skeleton, then run the first real quality gate.

## What was built

- `SKILL.md` — Agent Skills format (`name` / `description` / `license` /
  `metadata`), 8 short sections with progressive disclosure into `references/`.
  Description carries both English and Chinese trigger phrases.
- Repo contract: `README.md`, `README.zh-CN.md`, `LICENSE` (MIT),
  `CONTRIBUTING.md`, `CHANGELOG.md`, `requirements.txt` (Pillow only),
  `.gitignore`, `.github/workflows/ci.yml` (Python 3.9 / 3.11 / 3.12).
- Knowledge layer, distilled and de-identified from the four-round field
  archive: `workflow.md`, `sources.md`, `pitfalls.md` (~30 dated failure modes),
  `image-ops.md`, `fact-check.md` (two real misattribution cases),
  `delivery.md`, `meme-optional.md`, `optional-adapters.md`.
- `profiles/minimal.json` (default) + `profiles/editorial-wechat.json` (opt-in),
  with a documented schema. Compliance is a hard rule enforced by
  `load_profile()`; a profile can only add constraints.
- `examples/`: quickstart, a Chinese sample request walking through the
  semantic-query and fact-check reasoning, and a sample picks manifest.
- `tests/test_portability.py` — a permanent static gate, not a throwaway script.

## Design decisions recorded

1. **English-first product docs + full Chinese README.** Chinese query templates
   stay in Chinese because they are data, not prose.
2. **No private anything.** No project rule files, no personal ledgers, no
   machine-specific interpreter, no user names, no absolute home paths in
   shipped files. Enforced by a scanner.
3. **No real stills in the repo.** Test imagery is generated at runtime.
4. **Profiles can only tighten.** Provenance, subtitle annotation, dead-end
   logging and no-deletion are code-level rules, not preferences.
5. **Stills-first; memes are an appendix.** Anything needing a login is an
   optional adapter, never a dependency.

## Self-check: first run FAILED with 2 issues

```
FAIL: 2 issue(s) found
  [privacy] CHANGELOG.md:40 -> unresolved repository placeholder: 'your-account'
  [privacy] README.md:49    -> unresolved repository placeholder: '<your-'
```

Both were invented/repository placeholders that must not appear in a finished
release. Fixed by rewriting the install instructions without a fake clone URL
and removing the fabricated release link.

## Additional findings from a manual consistency walk (4)

| # | Problem | Fix |
|---|---|---|
| 1 | `SKILL.md` acceptance item said "No candidate was deleted **unless the active profile explicitly permits it**", contradicting the hard no-deletion rule. | Reworded to an unconditional "No candidate was deleted; intermediates retained". |
| 2 | `README.zh-CN.md` still used `git clone <你的仓库地址>`; the scanner only matched English placeholders and **missed it**. | Rewrote the snippet; added `git clone <` to the scanner so any language's placeholder in an install command is caught. |
| 3 | `.gitignore` had `!docs/**/*.png`, which would allow committing imagery and contradicted "no film stills in the repo"; also had dead `!examples/*.html` / `!profiles/*.json` exceptions. | Removed all four exceptions; the ignore list is now consistent with the asset check. |
| 4 | `references/pitfalls.md` D6 described a machine-specific deletion shim. | Generalised to "Some environments intercept file deletion". |

## Re-run

```
PASS: static portability checks (structure, frontmatter, links, privacy,
      no-deletion, profiles, no binary assets)
```

Checks covered: required file structure, SKILL.md frontmatter validity and body
length, every relative Markdown link resolving to a real file, private-path /
credential / placeholder scanning, no deletion calls in `scripts/`, profile JSON
schema and hard-rule enforcement, and absence of binary image assets.

## Deliberately deferred to round 2

`scripts/`, `tests/test_offline.py`, and the `--full` mode of the portability
gate. The gate currently runs in static mode so that a missing script does not
produce a misleading pass. CI already references the offline test; that
reference is validated in the round-3 full regression.

## Hand-off to round 2

Build the portable CLI so the docs stop describing commands that do not exist
yet — every command referenced in `SKILL.md`, both READMEs and `quickstart.md`
must be implemented and exercised.
