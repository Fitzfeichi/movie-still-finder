# Quickstart

A complete run, plus the three common variations. All commands work from the
repository root. Everything writes under the path you pass to `--out`; nothing
is written into the repository.

## Setup

```bash
python -m pip install -r requirements.txt
python scripts/still.py --help
python scripts/still.py rules          # which behaviours are active by default
```

## A. Mood / scene request (most common)

```bash
mkdir -p ./demo && cd ./demo

# 1) Reachability first. Dead hosts are recorded, not retried in a loop.
python ../scripts/still.py probe

# 2) Batch-download candidates from a gallery page verified in the field run.
#    --image-referer is the site root (image CDNs rarely accept the page URL).
python ../scripts/still.py grab --out ./work \
  --page "https://movie-screencaps.com/avatar-2009/page/114" \
  --image-referer "https://movie-screencaps.com/" \
  --limit 40
```

If `probe` reports this host as unreachable, pick another source from
`references/sources.md`, or use section D below for a run that needs no network
at all. This particular page begins with title cards, so raise `--limit` or
switch pages if the contact sheet contains no usable frames (pitfall C9).

`grab` produces:

```
work/
  candidates/p1_01.jpg ... p1_40.jpg
  contact_1.jpg            numbered contact sheet
  page_1.html              raw HTML, kept for re-extraction
  manifest.json            source page, direct URL, size, timestamp per image
```

```bash
# 3) VISION STEP. Open work/contact_1.jpg with a vision-capable model or your
#    eyes. Ask: "which number shows two people sitting apart, quiet, no text?"
#    Do not guess from filenames.

# 4) Prepare the winner.
python ../scripts/still.py crop work/candidates/p1_02.jpg --bottom 100 -o work/clean.jpg

# 5) Deliver with provenance.
cp ../examples/sample-picks.json ./picks.json    # edit ids to match your sheet
python ../scripts/still.py deliver ./work --picks ./picks.json --out ./delivery
```

## B. A line of dialogue

```bash
python scripts/still.py quote "I see you" --title Avatar
# -> sub id, film title, start_ms. Verify the line exists before searching.
```

If the original frame has no burned-in subtitle (usually the case with Blu-ray
frame libraries), composite one and **label it**:

```bash
python scripts/still.py subtitle ./frame.jpg "I see you" -o ./frame_subtitled.png \
  --note "subtitle composited, not native"
```

See `references/image-ops.md` for the gradient-vs-black-band rule.

## C. Cover art with a human editor

```bash
python scripts/still.py rules --profile profiles/editorial-wechat.json
python scripts/still.py deliver ./work --picks picks.json \
  --profile profiles/editorial-wechat.json --out ./delivery
```

Output:

```
delivery/
  selected/         the picks, renamed as specified in picks.json
  all-candidates/   EVERY downloaded frame, untouched, grouped by source
  cover_compare.jpg 2.35:1 crop comparison sheet
  manifest.json     provenance + processing steps
```

Nothing is deleted. The human can still pick a different frame from
`all-candidates/` later.

## D. Fully offline smoke test

Useful for CI, or when no network is available:

```bash
python tests/make_fixtures.py --out ./demo/fixtures
python tests/test_offline.py
python scripts/still.py verify
```

`verify` checks Pillow, font discovery, profile validity, and runs a tiny
in-memory pipeline. It never touches the network.

## Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| `probe` shows `403` | Paid / signed / anti-bot host | Switch source. Do not bypass. `references/sources.md` |
| `grab` extracts 0 URLs | Page renders images via JS, or returns a verification page | Use a page with plain `src`/`data-src`, or keep the full URL including all query parameters |
| Page returns 200 but every image is 403 | Image CDN hotlink policy; page reachability says nothing about the image host | Try `--image-referer "https://site.example/"` (site root, not the article URL). Still 403 -> switch source, do not keep varying headers |
| `Tunnel connection failed: 502 Bad Gateway` on a whole gallery | Network/proxy fault | One retry; if it persists, switch source. Unrelated hosts may still work |
| `ModuleNotFoundError: No module named 'PIL'` | A different Python interpreter than the one that installed the requirements | Install and run with the **same** interpreter: `python -m pip install -r requirements.txt && python scripts/still.py --help` |
| `width 768px is below min_width 1000` on delivery | Thumbnail gallery, not a defect | The warning is the rule working. Use `full <slug> <page> <frame-number>` to fetch the high-resolution original |
| Wondering where the unselected candidates went | Minimal profile does not copy the full candidate set | Nothing was deleted — the originals remain in `work/candidates`, and the CLI says so. Use `editorial-wechat.json` to also copy them into `all-candidates/` |
| Contact sheet is one long strip | Too many cells per sheet | `--per 42` limits cells per sheet |
| Picked frame has a subtitle bar | Viewing screenshot, not a clean frame | `crop --bottom 100`, then re-check visually |
| Fonts look tiny / boxes | No CJK font on the machine | `still.py` auto-discovers system fonts; pass `--font` explicitly |
| A host worked yesterday, fails today | Source drift | Record it with a date, add to `references/pitfalls.md`, switch source |

More failure modes, with exact error strings: `references/pitfalls.md`.
