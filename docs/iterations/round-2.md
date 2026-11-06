# Round 2 — portable CLI, offline end-to-end, live network check

**Date:** 2026-11-06
**Goal:** Make every command promised by the docs real, prove the full pipeline
offline, then prove it against live public sources without credentials.

## What was built

- `scripts/still_lib.py` — HTTP fetch (with a stop rule for 403), direct-URL
  extraction, in-memory image validation, concurrent download, numbered contact
  sheets, cross-platform font discovery, subtitle cropping/compositing, profile
  loading with hard-rule enforcement, provenance manifests, dual-folder
  delivery. Standard library + Pillow only.
- `scripts/still.py` — 11 subcommands: `probe`, `grab`, `sheet`, `quote`,
  `frames`, `full`, `crop`, `subtitle`, `deliver`, `rules`, `verify`.
- `tests/make_fixtures.py` — generates synthetic numbered images, one
  deliberately broken file, a local HTML page using `file://` URLs, and a picks
  manifest. No copyrighted imagery, no network.
- `tests/test_offline.py` — drives the **real CLI** end to end against those
  `file://` fixtures (30 assertions), including both profile layouts and hard
  rule rejection.

Key design choice: `fetch` supports `file://`, so the offline test is not a
mock. It exercises the same extract / download / sheet / crop / subtitle /
deliver code paths that a live run uses.

## Self-check results

```
verify                    PASS (Pillow, font, profiles, in-memory pipeline)
tests/test_offline.py     PASS: 30 offline end-to-end checks
tests/test_portability.py --full   PASS (after fix below)
compileall scripts tests  PASS
```

The 30 checks include: broken image rejected in memory and never written, two
numbered sheets, provenance on every candidate, crop dimensions, composited
subtitle labelling, single-folder vs dual-folder delivery, every candidate
retained, no source file touched, and a custom profile that disables a hard
rule being rejected.

**Environment note:** the machine's default `python` had no Pillow. Tests were
run with the pre-existing isolated interpreter that has Pillow 12.3.0; CI
installs from `requirements.txt` first. A troubleshooting row was added to
`examples/quickstart.md` for the "installed with one interpreter, ran with
another" trap.

### Scanner false positive (fixed)

`--full` first failed with 4 issues, all from `docs/iterations/round-1.md`,
which quotes the already-fixed placeholder strings verbatim. Iteration reports
legitimately quote historical findings. The scanner now treats `iterations/`
as a soft-scan directory: private paths and credentials are still checked,
placeholder/unfinished markers are not. Re-run passed.

## Live network verification (no login, no keys, no paid service)

`probe --timeout 10`: **6/7 hosts reachable** (film-grab timed out; the other
six returned 200).

| # | Attempt | Result | Decision |
|---|---|---|---|
| A | FilmGrab dedicated page | `502 Bad Gateway` | One documented retry |
| A2 | Same page, single retry | `502 Bad Gateway` again | **Stop. Switch source. No bypass.** |
| B | Sohu editorial article, article URL as Referer | page 200, 12 plaintext URLs, **12/12 images 403** | Diagnosed as a code defect (below) |
| C | Same article, site-root Referer | still 12/12 403 | **Stop. Switch source**, record as dead for this run |
| D | `quote "I see you" --title 阿凡达` | **SUCCESS** — 31 pages / 20 hits, `sub_id=13829`, millisecond timestamps, correct film | Verified |
| E | `full avatar-2009 114 20440` | **SUCCESS** — 1920x1080 JPEG, valid RGB | Verified |
| F | `screencapsmovie` gallery | page 200, 8 URLs, all `502 Bad Gateway` | **Stop.** Network-side fault |
| G | `grab` on a reachable frame gallery with `--image-referer` | **SUCCESS** — 9/10 valid images, numbered `contact_1.jpg`, `manifest.json` | Verified |

All live outputs were written to a system temporary directory, never into the
repository. No candidate was deleted.

### Visual re-check of the live outputs

- The `full` frame is the expected wide, subtitle-free *Avatar* close-up
  (Neytiri leaning over the human-form Jake), matching the documented example.
- The `grab` contact sheet had **9 readable numbered cells, but 8 were title
  logos and site decorations**; only one showed a character. This is a clean
  real-world confirmation that a "9/10 valid" download is not a semantic match
  and that the vision-picking step cannot be skipped. Recorded as pitfall C9.

## Real defect found and fixed

`grab` used the **page URL** as the Referer for image CDN requests. Image CDNs
normally expect the site root. Fixed by splitting the two concepts: page
requests still use the page URL; image requests default to the URL's origin
(`scheme://host/`) and can be overridden with `--image-referer`. Offline tests
still pass unchanged. Note that this did **not** rescue the Sohu CDN in this
environment — the correct behaviour after a second 403 was to switch source,
which is what the tool and the docs now say.

## Knowledge layer updated with dated findings

- `sources.md`: Sohu row now records "page 200 / all images 403 as of
  2026-11-06"; `screencapsmovie` row records the 502; "re-verify a source"
  now explicitly warns that `probe` checks the page host, not the image CDN.
- `pitfalls.md`: added B9 (page 200 but every image 403), C9 (hit count is not
  semantic match), D11 (widespread 502 through a proxy, switch after one retry).
- `quickstart.md`: troubleshooting rows for image-CDN 403, 502, and the Pillow
  interpreter mismatch.
- `SKILL.md` rule 2: "a reachable page does not mean its image CDN is
  reachable".

## Unresolved (recorded, not papered over)

- FilmGrab and two Blogger-backed image hosts were unreachable from this
  environment during this session (`502 Bad Gateway` / timeout). They remain
  documented as high-priority sources for other environments; availability is
  date-stamped and `probe` exists precisely for this.
- The Sohu image CDN rejected all requests even with the site-root Referer.
  No further header variation was attempted, per the two-strikes rule.

## Hand-off to round 3

The docs currently use a FilmGrab URL as the headline example, which just
failed the live check. A brand-new agent following the README would hit the
same wall. Round 3 must validate the docs from a stranger's point of view and
replace any example that cannot be run right now.
