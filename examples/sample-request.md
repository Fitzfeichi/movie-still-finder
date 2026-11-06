# A sample request, end to end

This is the shape of a real editorial request. It is deliberately Chinese,
because the search templates for Chinese-language film coverage are themselves
Chinese data.

> 文章讲「人与人之间无法百分之百理解，但不理解也可以尊重」。
> 想找一张剧照做封面：两个人并肩坐着、各望一方、安静、没有字幕，宽幅能压标题。

## 1. Fact-check before searching

Is there a specific film/line/scene claim? Here there is none — it is a mood
request, so there is nothing to misquote. But note a related trap: a widely
circulated "still of the boy's bald spot from *Yi Yi*" is a **re-staged DVD
cover photo**, not a frame from the film. If you had asked for that as a still,
the honest answer is "it is not a still".

For line-based requests, always verify title, year, episode/scene, original
wording and speaker. See `references/fact-check.md`.

## 2. Turn semantics into queries, not literal nouns

Do not search "无法百分之百理解". Search what the camera shows:

```
"<片名>" 并肩 OR 各望一方 剧照 影评
"<片名>" 结尾 和解 画面 观后感
site:mp.weixin.qq.com "<片名>" 沉默 影评
"<Film>" final scene reconciliation still
```

Avoid the word 截图 in Chinese image search: engines drift toward software
screenshots. Prefer 画面 / 剧照 / 观影截图 / 場面 / キャプチャ.

## 3. Pick a source by request type

Mood + clean wide frame + no subtitles -> curated frame gallery first
(FilmGrab or a frame-by-frame gallery), editorial article with captioned stills
second. Run `python scripts/still.py probe` first to see which hosts answer —
sources drift, so substitute whichever source is reachable for you.

## 4. Batch, sheet, vision pick

```bash
# Replace the page with one from your own probe results; the URL below was
# reachable during the 2026-11-06 field run.
python scripts/still.py grab --out ./work \
  --page "https://movie-screencaps.com/avatar-2009/page/114" \
  --image-referer "https://movie-screencaps.com/" \
  --limit 60
# open work/contact_1.jpg ... work/contact_2.jpg with a vision model
```

Read the number from the actual sheet. "First row, second column" must be
resolved against the sheet layout, not the filesystem order.

## 5. Prepare and deliver

```bash
python scripts/still.py crop work/candidates/p1_02.jpg --bottom 100 -o work/clean.jpg
python scripts/still.py deliver ./work --picks picks.json \
  --profile profiles/editorial-wechat.json --out ./delivery
```

With `editorial-wechat`, `deliver` produces `selected/` + `all-candidates/`
(every downloaded frame, nothing deleted) plus a 2.35:1 comparison sheet, and
writes provenance into `delivery/manifest.json`.

## 6. Acceptance

- The image opens and actually shows two people, quiet, facing different ways.
- No residual subtitle or watermark; if a subtitle was composited, it is labelled.
- Width >= 1000 px.
- `manifest.json` has source page and direct URL.
- Dead hosts are recorded in the run notes, not silently retried.
