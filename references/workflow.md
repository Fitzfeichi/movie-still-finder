# End-to-end workflow

Self-contained SOP. An agent that reads only this file and `SKILL.md` can run a
complete job. Other reference files add detail on demand.

## Before you start: classify the request

| Type | First route | Fallback |
|---|---|---|
| Scene / mood | Editorial article with captioned stills, or curated frame gallery | Frame-by-frame library + visual page scanning |
| Quoted line | Public subtitle-seek endpoint -> timestamp -> frame library -> subtitle composite | Screenshot with native subtitle from an editorial article |
| Requires native burned-in subtitle | Editorial viewing screenshots | Clean frame + composited subtitle (label it) |
| Requires clean wide cover frame | Curated frame gallery | Crop bottom 95-100 px off a viewing screenshot |
| Local video files available | Optional local semantic index, see `optional-adapters.md` | — |

## Steps

**1. Align on the deliverable.** Real image files or links only? Native or
composited subtitles allowed? Are adjacent frames from the same scene OK?
Personal draft or public publication? How recognisable must the film be?
Do not assume — a wrong assumption here invalidates all later work.

**2. Fact-check.** For any specific line or scene, verify title, year,
episode/scene, original wording and speaker with 2-3 independent searches.
Widely repeated summaries are frequently wrong. See `fact-check.md`.

**3. Probe reachability.** `still.py probe` checks the hosts in
`sources.md` with a short timeout. Record every non-200 result with a date.
A 403 is a decision to switch source, not a debugging challenge.

**4. Create a workspace.** `grab --out ./work` creates `candidates/`, keeps the
raw HTML, and writes `manifest.json`. Keep intermediates; do not tidy up.

**5. Search by meaning, not literal nouns.** Translate the paragraph's emotional
relationship into something a camera can show. Use several short queries in
parallel rather than one long sentence. Store result URLs as JSON so the run is
reproducible. Query templates: `sources.md`, `examples/sample-request.md`.

**6. Extract direct image URLs and download.** Use 10-12 workers with a 12-20 s
per-image timeout; 170 images downloaded serially will time out. **Validate in
memory** (`Image.open(BytesIO(data))`, check minimum dimensions) before writing
anything to disk — bad responses and decoration icons are common. Never invent
a URL; only download what a page actually returned.

**7. Build a numbered contact sheet.** 200-300 px cells, 42-70 cells per sheet,
number printed under each cell, original aspect ratio preserved (do not crop
away subtitles in the preview). `still.py grab` and `still.py sheet` do this.

**8. VISUAL PICK — cannot be skipped.** Show the sheet to a vision-capable model
or the human and ask which number matches the scene. Resolve "first row, second
column" against the actual sheet layout, never against filesystem order. Pure
text guessing from filenames fails.

**9. Get the high-resolution original.** Find the full-size URL template in the
gallery page and substitute the frame number. Mind the `Referer` and CDN size
parameters. With curated galleries, adjacent numbers are often the same frame
at different resolutions — skip through the sheet rather than taking neighbours.

**10. Image processing** as needed: crop burned-in subtitles/watermarks, or
composite a subtitle. See `image-ops.md`. Always state in the output what was
done.

**11. Visual re-check of the single file.** People, orientation, residual text,
over-cropping, width >= 1000 px, file opens correctly.

**12. Deliver + provenance + log.** `still.py deliver` writes selected images,
a manifest with source page / direct URL / film / processing steps, and — when
the active profile asks for it — the full candidate set and a cover comparison
sheet. Record dead hosts, workarounds and unresolved items with a date so the
next run starts smarter. See `delivery.md`.

## Acceptance checklist

- [ ] Line / scene fact-checked; no reliance on a secondary summary
- [ ] A numbered contact sheet was visually inspected
- [ ] Final image matches the *meaning* of the request, not just the query words
- [ ] Source page, direct URL, film title/year recorded
- [ ] Cropped / composited subtitles explicitly labelled
- [ ] Width >= 1000 px (or the deviation stated), file opens
- [ ] If several images: avoid two from the same film unless accepted
- [ ] Dead hosts, workarounds and unresolved items recorded
- [ ] No candidate deleted; intermediates retained

## Time-savers that are actually true

- Captions in editorial articles are a free, human-labelled "scene -> image"
  dataset. This is why the article route beats raw image search for mood requests.
- Curated frame galleries beat frame-by-frame libraries for covers: fewer,
  cleaner, wider frames.
- One retry is reasonable for a transient `502 Bad Gateway`. A `403` is not
  transient — switch source.
- If a source requires a signature, a token, or a logged-in browser, it is an
  optional adapter, not part of this pipeline.
