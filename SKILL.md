---
name: movie-still-finder
description: >-
  Find film stills / movie screenshots from a scene description, a mood, or a line
  of dialogue, and deliver clean, sourced, numbered candidates for editorial use.
  Use when the user asks for 剧照 / 电影剧照 / 电影截图 / 影视截图 / 影片帧 / 文章配图 / 封面 /
  movie still / film frame / screencap / "find a frame where ..." / "illustrate this
  paragraph", or wants to verify whether a quoted line really occurs in a film. Covers
  fact-checking, source scouting, batch download, numbered contact sheets,
  visual frame picking, cropping burned-in subtitles, and subtitle compositing.
  Agent-agnostic: no account, no API key, no browser login, no paid service.
  Requires Python 3.9+ and Pillow only. Meme/梗图 lookup is an optional appendix.
license: MIT
metadata:
  version: "1.1.0"
  displayName: "Movie Still Finder"
  scope: agent-agnostic
  category: media
  author: Fitzfeichi
  tags:
    - movie-stills
    - film-screenshots
    - film-frames
    - screencaps
    - image-search
    - article-illustration
    - cover-art
    - agent-skill
    - claude-code
    - cursor
    - codex
  default_profile: profiles/minimal.json
---

# Movie Still Finder

Turn "I need a still of two people sitting in silence after an argument" into a
real, sourced image file. Any AI agent, any OS, no credentials.

## 1. Read this first: what is actually possible

There is **no** free public API that takes a natural-language sentence and returns
the exact film frame, especially one with burned-in dialogue subtitles. Chasing
that "silver bullet" wastes time. What works is a **pipeline**, where the agent
orchestrates and a vision-capable model picks the frame:

```
request -> fact-check -> choose source -> batch-download candidates
        -> numbered contact sheet -> VISUAL frame picking -> high-res original
        -> crop subtitles / composite subtitle -> visual re-check
        -> delivery + source manifest
```

Two non-negotiable consequences:

- **The vision step cannot be skipped.** Guessing a frame from filenames or text
  alone fails. Show the contact sheet to a vision-capable model (or the human).
- **Fact-check first.** Widely repeated "facts" about films are often wrong (see
  `references/fact-check.md`). Verify the line / scene / episode before searching.

## 2. Quick start (minimal profile, the default)

```bash
pip install -r requirements.txt
python scripts/still.py probe                       # which sources are reachable right now
python scripts/still.py grab --out ./work \
  --page "https://movie-screencaps.com/avatar-2009/page/114" \
  --image-referer "https://movie-screencaps.com/" \
  --limit 40
# -> ./work/candidates/*.jpg, ./work/contact_1.jpg, ./work/manifest.json
# Show contact_1.jpg to a vision model, note the winning number, then:
python scripts/still.py sheet ./work/candidates     # regenerate a numbered sheet
python scripts/still.py crop ./work/candidates/p1_02.jpg --bottom 100 -o ./work/clean.jpg
python scripts/still.py deliver ./work --picks examples/sample-picks.json \
  --profile profiles/minimal.json --out ./delivery
```

Always run `probe` first: source availability drifts. For a fully offline run,
see section D of `examples/quickstart.md`. `--image-referer` is normally the
site root, not the article URL.

For a line of dialogue, `quote` gives film + millisecond timestamp:

```bash
python scripts/still.py quote "I see you" --title Avatar
```

Full walkthrough: `examples/quickstart.md`. Command reference: `scripts/still.py --help`.

## 3. Decide the route before touching the network

| Request | First choice | Fallback |
|---|---|---|
| Scene / mood ("silence after a fight", "two people facing away") | Editorial article with captioned stills, or FilmGrab curated frames (`grab`) | Frame-by-frame gallery + visual picking |
| A quoted line / "the frame where X says Y" | `quote` → timestamp → frame gallery → `subtitle` (label as composited) | Screenshot with native subtitles from an editorial article |
| Needs wide, clean, subtitle-free cover art | FilmGrab curated frames | `crop` the bottom 95-100 px off a viewing screenshot |
| User has local video files | Optional local semantic search, see `references/optional-adapters.md` | — |
| Meme / 梗图 rather than a still | Optional appendix, `references/meme-optional.md` | — |

Run `probe` first. It is free, needs no login, and tells you which sources are
403 / unreachable in your environment so you do not retry a dead host.

## 4. Rules that hold for every agent

1. **No credentials.** Do not ask for API keys, do not log in on the user's
   behalf, do not bypass paywalls or anti-bot protections. A 403 means "switch
   source", recorded in the run log.
2. **Download only URLs that were actually returned.** Never invent an image URL.
   A reachable page does not mean its image CDN is reachable: verify one image
   before trusting a whole gallery. If images 403 after one Referer correction,
   switch source — do not keep varying headers.
3. **Record provenance.** Every delivered image needs source page, direct image
   URL, film title/year, and whether any subtitle was cropped or composited.
   `grab` writes this to `manifest.json` automatically.
4. **Mark composited subtitles.** If you add a subtitle that was not in the
   original frame, say so in the caption. Never present it as a native frame.
5. **Verify, don't assume, resolution** (>= 1000 px wide by default) and open the
   final file with a viewer before delivering.
6. **Respect the profile.** Behaviour beyond the above (human-in-the-loop
   selection, dual-folder delivery, mandatory fact-check, cover-crop preview) is
   controlled by `profiles/*.json`. Do not silently enable extra rules.

## 5. Profiles (optional behaviour)

The default `profiles/minimal.json` is a plain, general-purpose pipeline: find
candidates, pick one, deliver with provenance. Everything else is opt-in.

```bash
python scripts/still.py rules --profile profiles/editorial-wechat.json
python scripts/still.py deliver ./work --picks picks.json \
  --profile profiles/editorial-wechat.json --out ./delivery
```

`editorial-wechat.json` bundles a human editor's workflow: numbered previews and
human selection (never auto-finalize), **dual-folder delivery with zero candidate
deletion**, mandatory fact-check, mandatory subtitle/source annotation, and a
2.35:1 cover-crop preview. See `profiles/README.md` for the full schema.

## 6. Reference index (progressive disclosure)

Read only what the current step needs.

| File | Read when |
|---|---|
| `references/workflow.md` | You need the full end-to-end SOP and acceptance checklist |
| `references/sources.md` | Choosing a source, or a source stopped working |
| `references/pitfalls.md` | Something failed; contains the known-dead hosts and exact failure modes |
| `references/image-ops.md` | Contact sheets, cropping, subtitle compositing, fonts |
| `references/fact-check.md` | Any request quoting a line or describing a specific scene |
| `references/delivery.md` | Provenance schema, dual-folder layout, copyright boundary |
| `references/meme-optional.md` | User asked for a meme instead of a still |
| `references/optional-adapters.md` | Local video library, or other login/CLI based tools |

## 7. Acceptance checklist

- [ ] The line / scene was fact-checked before searching
- [ ] A numbered contact sheet was looked at by a vision model or the human
- [ ] The final image opens correctly and matches the request, not just the query
- [ ] Source page + direct URL + film/year recorded in `manifest.json`
- [ ] Cropped / composited subtitles explicitly labelled
- [ ] Width >= 1000 px (or the deviation is stated)
- [ ] Dead hosts and workarounds recorded rather than silently retried
- [ ] No candidate was deleted; intermediates retained

## 8. Scope limits

This skill finds and prepares images. It does **not** publish anything, edit the
user's manuscript, decide the final cover on the user's behalf (unless the
profile says the human already chose), or grant any right to redistribute film
stills. See `references/delivery.md` for the copyright boundary.
