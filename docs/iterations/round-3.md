# Round 3 — stranger's-eye review, doc executability, publishability

**Date:** 2026-11-06
**Goal:** Judge the repo as someone who has never seen this project: can they
clone it and get a real result in five minutes by copy-pasting the README?
Then verify compliance and publishability.

## Method

1. **Command audit.** Grepped every `still.py <cmd>` occurrence in all product
   docs and compared against the CLI's actual subcommand list and `--help`.
2. **Copy-paste run.** Executed the README's 60-second example verbatim from a
   clean temporary directory outside the repository (absolute CLI path, so no
   downloaded image could land in the repo).
3. **Full regression.** Offline end-to-end, full portability scan, byte compile,
   `--help` for all 11 subcommands, both profiles, JSON validity.
4. **Publishability.** `git init`, inspect what would be committed and whether
   ignore rules actually exclude generated imagery.

## Findings and fixes

| # | Finding | Fix |
|---|---|---|
| 1 | **Four documents used FilmGrab as the headline example** — the exact host that returned `502 Bad Gateway` in round 2. A stranger's first command would fail. | `README.md`, `README.zh-CN.md`, `SKILL.md`, `quickstart.md` now use a page verified reachable in the field run, include the required `--image-referer`, and tell the reader to run `probe` first + point to the fully offline route. |
| 2 | `references/meme-optional.md` showed `grab --page "<image-search-or-meme-page-url>"`, which does not work: image-search result pages hide URLs in script attributes, not `img` tags. | Replaced with an honest explanation and the supported route (a plain HTML page of direct URLs, `file://` supported; `make_fixtures.py` shows the shape). |
| 3 | `examples/sample-request.md` used `<gallery-or-article-url>` inside an apparently runnable command. | Replaced with a real URL plus an explicit "replace with your own probe results" comment. |
| 4 | `examples/sample-picks.json` named a film unrelated to the documented example source. | Neutralised film names, added a `_comment` explaining that ids must match the user's own sheet. |
| 5 | Live `grab` emitted a Pillow warning for P-mode images with byte transparency. | `validate_image()` now routes those through RGBA before RGB. CLI output stays clean. |
| 6 | `deliver` printed `0 candidates kept` under the default profile — easy to misread as "the tool deleted them". | Output now states that candidates are untouched in `work/candidates` and nothing was deleted. |
| 7 | A `min_width` warning on thumbnail galleries had no explanation in the newcomer docs. | Both READMEs explain it and point to `full`; quickstart troubleshooting gained two rows (min_width, and where unselected candidates live). |
| 8 | The portability scanner's soft-scan rule for iteration reports (round 2) needed re-verification after new docs were added. | Re-ran `--full`; passes. |

## Copy-paste run result

```
grab    [page 1] 40 image URLs -> 23/40 valid images
        contact_1.jpg, manifest.json
crop    work/clean.jpg (1920, 980)
deliver 2 selected -> delivery/
manifest  layout=single-folder, selected=2, sources present=True
```

The one warning (`width 768px is below min_width 1000`) is the profile rule
working as designed on a thumbnail; it is now documented. No image was written
into the repository during this run.

## Full regression

```
tests/test_offline.py            PASS: 30 offline end-to-end checks
tests/test_portability.py --full PASS (structure, frontmatter, links,
                                 privacy, no-deletion, profiles, no assets)
compileall scripts tests        PASS
11/11 subcommand --help         PASS
rules (both profiles)           PASS
all JSON files                  valid
```

## Publishability

`git init` completed (the parent directory is not a git repository, so there is
no nesting). 15 top-level entries would be committed. `git check-ignore`
confirms generated fixtures are excluded, and no image file appears in the
untracked list. **No commit, no remote, no push was performed** — publishing
needs the user's explicit authorisation and a repository URL.

## Honest remaining gaps

- GitHub Actions has not actually run on GitHub; the workflow is written and
  its commands were executed locally on Python 3.13. Matrix entries for 3.9 /
  3.11 / 3.12 are unverified on those interpreters.
- `frames` was verified by `--help` and the offline suite, but not against a
  live gallery (`full`, `grab` and `quote` were verified live).
- FilmGrab and two Blogger-backed image hosts were unreachable from this
  environment during this session. They remain documented with dates; `probe`
  exists for exactly this situation.
- `quote` results need human filtering: `title_filter` is a soft ranking, and
  the endpoint returns loosely matched subtitle rows.
- Product docs are English-first; the Chinese counterpart is `README.zh-CN.md`.
  Chinese search-query templates stay in Chinese because they are data.
- No issue templates, release automation, or community code of conduct. These
  are nice-to-have for an established project, not required for a first release.

## Hand-off

Three rounds are complete. The repo is self-contained, credential-free,
portable, offline-testable, and live-verified. The remaining decision belongs
to the user: choose a repository name/licence holder, add a remote, and push.
