# Data sources

Verified in a four-round field run on 2026-11-05/06 from a Windows host.
**Availability drifts.** Always run `still.py probe` first and record what your
environment actually sees. A date-stamped observation beats a stale table.

## Priority table

| Priority | Source | Provides | Required parameters / headers | Limits |
|---|---|---|---|---|
| best | **Curated frame galleries** (`film-grab.com`) | 100+ clean, wide, subtitle-free frames per film | Search: `https://film-grab.com/?s=<title>`; extract `https://film-grab.com/20\d\d/\d\d/\d\d/[a-z0-9-]+`; images are `i0.wp.com/...` or `wp-content/uploads/...`, no Referer needed | Not every film has a page (older/classical titles often missing); the same frame appears at 5-6 sizes, so adjacent IDs can be duplicates |
| best | **Editorial articles with captions** (Chinese media, WeChat articles, film blogs) | Viewing screenshots + caption text; best semantic match for mood | WeChat: full URL including `&chksm=...`; extract `data-src="https://mmbiz.qpic.cn/..."`; download with `Referer: https://mp.weixin.qq.com/` | Anti-scraping and permission policies vary; JS-rendered bodies return no images; screenshots usually carry subtitles/watermarks |
| good | **Portal articles** (Sohu, Sina, Tencent) | Plain image links + captions | Sohu `data-src` is obfuscated: use the plaintext URL list at the page tail, which follows body order | Toutiao and Bilibili columns keep images in JS or behind an anti-bot page. **2026-11-06 re-check:** the Sohu article page returned 200 and exposed 12 plaintext `p*.itc.cn` URLs, but every image request returned 403 with both the article URL and the site root as `Referer`. Page reachability does **not** prove image availability — switch source |
| good | **Frame-by-frame libraries** (`movie-screencaps.com`) | Exact frame by number, 1920x1080 | Gallery `/{slug}/page/{N}`, 180 frames/page; thumbnails `caps2.b-cdn.net/...-{N}.jpg?class=thumbnail` with `Referer: https://movie-screencaps.com/`; full size `i0.wp.com/imgs.screencaps.us/...-{N}.jpg?ssl=1` | Commercial theatrical films only; **no Netflix / arthouse titles** |
| good | `screencapsmovie.com` | Arthouse curated frames, ~1329 px clean | Each frame has two size links; take the `s1329` one from `blogger.googleusercontent.com/img/b/...`; `Referer: https://www.screencapsmovie.com/` | Smaller catalogue. **2026-11-06:** the gallery page was reachable but its `blogger.googleusercontent.com` / `1.bp.blogspot.com` images returned `502 Bad Gateway` through the network proxy; verify one image before trusting the whole page |
| good | `allscreencaps.com` | Broad thumbnail catalogue | `/mobile/intro/{id}.html`; images at `http://img.allscreencaps.com/uploads_s/{id}/s/...jpg` — **http, not https** | Some films return non-image content; validate each file in memory |
| good | Public subtitle-seek endpoint (`zhaotaici.cn`) | Line -> film + millisecond timestamp | `php/api/subtitle_seek_api.php?action=seek_all&search_type=text&query=<words_joined_by_>&is_en=1&pageNum=0`; response `items[].sentence.json_sub_item.{start,end,zh,en}`, `start` in **ms**; `title_filter` is a soft ranking, not a hard filter | Its screenshot endpoints frequently return 500 / COS 404; do not sink time into them, go to a frame library instead |
| fallback | General image search (Bing) | Direct image URLs | `https://www.bing.com/images/search?q=...&form=HDRSC2&first=1&mkt=zh-CN` (or `mkt=en-US` for short English queries); parse `m="{...}"` with `json.loads(html.unescape(m))["murl"]` | Severe semantic drift, especially for Chinese film queries; always visually re-check |
| fallback | Baidu image `acjson` | Chinese candidates | `image.baidu.com/search/acjson?tn=resultjson_com&...&word=...&rn=30`; parse with `json.loads(t, strict=False)` (invalid escapes present) | Rate-limits quickly and then returns 0 results |

### Finding a gallery slug

Do **not** guess slugs. In-site `?s=` search often returns nothing. Use an
external search instead:

```
site:movie-screencaps.com "<Film> (<year>)"
site:screencapsmovie.com "<Film>"
site:allscreencaps.com "<Film>"
site:film-grab.com "<Film>"
```

Take the exact URL from the results. Four guessed slugs in a row once produced
four 404s before switching to this method.

## Known-unreachable / not usable (as of 2026-11-06)

| Host | Status | Reason |
|---|---|---|
| `shotdeck.com` | 403 | Paid subscription, no public API |
| `getyarn.io` | 403 | Cloudflare |
| PlayPhrase.me public API | 403 | `check-bot` anti-bot; human web UI only |
| 33台词 | signed | Requires `X-Token` + `X-Signature` + login |
| Criterion / TMDB web | 403 | Do not bypass |
| GitHub API unauthenticated | rate limited | search 10/min, repos 60/hour; use `raw.githubusercontent.com` for READMEs |

**Rule:** a 403 / signature wall is a decision to switch source. Do not attempt
an equivalent workaround, do not retry in a loop, and record it with a date.

## Choosing between sources

- Cover, wide, clean, no text -> curated frame gallery.
- "Two people after a fight", "quiet reconciliation", any mood -> editorial
  article with captions.
- "The exact frame at 01:02:19 where X says Y" -> subtitle-seek + frame library.
- Anime / TV episode captions -> editorial article; general image search returns
  logo cards, fan art and text infographics instead of frames.
- Anything Chinese-language -> prefer editorial articles over image search.
  Chinese queries containing 截图 drift to software screenshots.

## Adding or re-verifying a source

1. `python scripts/still.py probe` (or `curl -L -s -o /dev/null -w "%{http_code}"`).
   **This only checks the page host, not the image CDN.**
2. Fetch one page, download **one image**, open it in memory, note required headers.
   A 200 on the article plus 403 on every image is a dead source for that run.
3. Update this table with the date. If it fails, add it to `pitfalls.md`.

## Query templates

```
# Chinese film / TV, mood
"<片名>" 并肩 OR 沉默 OR 和解 剧照 影评
site:mp.weixin.qq.com "<片名>" <场景关键词> 影评 / 观后感
"<片名>" 第N话 OR 最终话 表白 画面 影评

# English, scene
"<Film>" final scene reconciliation still
"<Film>" "I see you" final scene screenshot

# Gallery discovery
site:film-grab.com "<Film>"
```

Prefer 画面 / 剧照 / 观影截图 / 場面 / キャプチャ over 截图 in Chinese image
search. Short phrases beat full sentences; abstract concepts beat nobody.
