# Delivery, provenance and copyright

## Two layouts

**Default (`minimal.json`)** — `single-folder`:

```
delivery/
  selected/       the picked images, renamed as specified in picks.json
  manifest.json   provenance + processing steps
```

**With `editorial-wechat.json`** — `dual-folder`:

```
delivery/
  selected/         the picked images (may be renamed, cropped, sampled)
  all-candidates/   EVERY other downloaded image, untouched, grouped by source
  cover_compare.jpg 2.35:1 crop comparison of the picks
  manifest.json
```

The reason for the second folder is simple and worth keeping: after a selection
is made, the human often wants a different frame from the rejected pile. A
"reject" is a decision about `selected/`, **not** permission to delete.

Rules:

- The full candidate set is copied, not filtered, renamed or deduplicated.
  Duplicate resolutions of the same frame are expected and stay.
- Intermediate products (raw HTML, contact sheets, candidate directory) are
  retained. Do not tidy up for the sake of neatness.
- No script in this repository calls a delete operation.
- State the two folders and their counts in the delivery text, and explicitly
  say the human can pick again from `all-candidates/`.

## picks.json

```json
{
  "request": "what the image is for",
  "profile_hint": "editorial-wechat",
  "picks": [
    {
      "id": "p1_02",
      "as": "01_cover.jpg",
      "film": "Film Title (year)",
      "note": "why this frame",
      "processed": "none | cropped 100px bottom | subtitle composited",
      "anchor": 0.22
    }
  ]
}
```

`id` must match a candidate id in the numbered contact sheet and in
`work/manifest.json`. `as` is the delivered filename. `anchor` optionally
overrides the profile's crop anchor for cover comparison.

## manifest.json schema

`grab` writes a per-workspace manifest; `deliver` writes a per-delivery one.

```json
{
  "generated_at": "2026-11-06T12:00:00Z",
  "profile": "editorial-wechat",
  "request": "...",
  "sources": [
    { "page": "https://...", "fetched_at": "...", "status": 200, "urls_found": 120 }
  ],
  "items": [
    {
      "id": "p1_02",
      "file": "selected/01_cover.jpg",
      "source_page": "https://...",
      "source_image": "https://.../frame.jpg",
      "film": "Film Title (year)",
      "width": 1329,
      "height": 720,
      "processed": ["cropped 100px bottom"],
      "subtitle_composited": false,
      "note": "..."
    }
  ],
  "dead_ends": [
    { "host": "example.com", "status": 403, "action": "switched source" }
  ]
}
```

An image without `source_page` + `source_image` is **not** a deliverable. If a
page did not expose a licence field, record the licence as `unknown` rather than
implying permission.

## What the delivery text must say

1. What each folder contains and how many images are in it.
2. Source page and direct URL per image (or a pointer to `manifest.json`).
3. Film title and year; episode/scene when relevant.
4. Whether a subtitle was cropped, or composited (composited = **not** a native
   frame), and whether a watermark was removed.
5. Any deviation from the request, and why (e.g. "the requested line does not
   exist in the film; this is the adjacent real scene").
6. Dead hosts and workarounds.
7. The copyright boundary below.

## States are not interchangeable

`candidate` / `selected` / `inserted into the article` / `published` are
different states. Delivering a selected image is not a claim that it was
published. This skill never publishes and never edits the manuscript.

## Copyright boundary

- This repository ships **no film stills**. The images a user obtains are
  third-party material governed by their own rights.
- Frame-by-frame libraries, editorial screenshots and promotional stills belong
  to the studios / publishers. Downloading for personal study, or as a draft
  illustration, is not a licence to redistribute or publish.
- Paying for an API or a search service does **not** buy the copyright to its
  images.
- A composited subtitle is a derivative work: label it so readers are not
  misled into thinking the line appears in the original frame.
- Before public release, obtain permission or switch to official/press
  materials. Mark unreverified licences as `unknown`.
- Hosts that block automated access are recorded and skipped. Do not bypass
  access controls, and do not represent a bypassed source as usable.

For a Chinese long-form article, a conservative practical rule: keep the source
record with the draft, and decide the publication path with the rights holder
before an image goes live.
