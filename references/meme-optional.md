# Optional: memes / 梗图 instead of a still

This skill is **stills-first**. Use this appendix only when the user explicitly
wants a meme, or when a paragraph needs a joke rather than a cinematic frame.
It is deliberately kept out of the main pipeline: meme sources change faster,
often need an account, and are much less reproducible than frame galleries.

## No-login path (the only supported default)

There is no "semantic meme API" in the default path. Also note that general
image-search result pages usually keep their image URLs inside a script
attribute instead of plain `img` tags, so pointing `grab` straight at a search
results page commonly returns zero URLs. Do not present that as a working step.

The supported route is a plain HTML page containing **direct** image URLs. Get
those URLs yourself (from a meme page that exposes plain `src` / `data-src`, or
from an image search's `murl` values), put one `<img src="...">` per line in a
local file, then let `grab` do the rest — it supports `file://` pages:

```bash
# page.html: <img src="https://example.org/meme1.jpg"> ...
python scripts/still.py grab --out ./work \
  --page "file:///absolute/path/to/page.html" --limit 30
```

`tests/make_fixtures.py` generates exactly such a page (with synthetic images)
if you want to see the shape first. Then the same vision loop as for stills
applies: numbered contact sheet -> look at it -> pick by number.

## Judgement rules that transfer from the field run

- Read the **whole paragraph** and translate its turn, irony or emotion into an
  image idea. Do not search the literal nouns. A sentence about "being late for
  a meeting" maps to frantic calculation and anxiety, not a clock.
- Short phrases beat full sentences; abstract concepts rarely beat a concrete
  situation. Look at a few results first — if they are off-topic, change the
  query direction instead of pulling more of the same.
- Textless or Chinese-language images are usually easier to place in a Chinese
  article. A perfect English meme can be explained or re-lettered if the user
  agrees.
- Image count follows the rhythm of the article. Do not pad to a round number.
- A recommendation is not a selection. Show numbered previews and let the human
  choose.
- Keep every candidate. See `delivery.md`.

## Re-lettering / translating a meme

Only if the agent's environment has an image editing tool, and only after
**opening the actual source image** first. A prompt should specify exact
wording, line breaks, top/bottom order, font style, outline, placement, and
which people, composition, white border and watermark must be preserved.

After generation, check for typos, word order, occluded faces and unchanged
characters. Keep the original and every version. An AI edit is not a promise of
pixel-level fidelity, and the result is a derivative image — say so.

## Services that require a login

Some meme libraries offer a CLI with a free quota and a browser-based
authorisation flow. They are **optional adapters**, not dependencies:

- Never ask the user to paste an API key into a chat or a repository.
- Authorisation is performed by the user themselves; credentials stay in the
  tool's own config directory, outside the project.
- If a saved login expires, re-authorise once through the official flow. Do not
  loop, and do not escalate filesystem permissions to fix it.
- Quota and pricing are date-stamped snapshots — check the current account.
- If the service is unavailable, fall back to general image search. A missing
  login must never block the whole task.

See `optional-adapters.md` for the general adapter policy.

## When to switch back to a still

If two rounds of meme search return literal matches, off-topic jokes, or
nothing usable, the paragraph probably wants a still. Switch route and say why,
rather than forcing a weak meme into the article.
