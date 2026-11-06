# Accumulated failure modes

Every entry below was observed in a real run (field rounds 1-4, 2026-11-05/06).
Read this before debugging. The fastest fix is usually "switch source", not
"make this host work".

## A. Hosts that will not cooperate

| # | Symptom | Cause | Action |
|---|---|---|---|
| A1 | `shotdeck.com` 403 | Paid, no public API | Switch. Its multimodal search is a commercial product |
| A2 | `getyarn.io` 403 | Cloudflare | Switch |
| A3 | PlayPhrase.me public API 403, `check-bot.min.js` | Deliberate anti-bot | Web UI only; do not write an API client |
| A4 | 33台词 API needs `X-Token` + `X-Signature` | Signature = sorted params -> `k=v,` join -> hash, plus login | Not worth reverse-engineering; use the public subtitle-seek endpoint |
| A5 | Criterion / TMDB / festival sites 403 | Access control | Switch; do not use an equivalent workaround |
| A6 | GitHub API 200 then 403 | Unauthenticated limits: search 10/min, repos 60/hour | Use `raw.githubusercontent.com` for READMEs; do not retry |
| A7 | `hdpian.com` `CERTIFICATE_VERIFY_FAILED` | Incomplete certificate chain | Treat as unreliable; prefer a different host |

## B. Extracting image URLs from pages

| # | Symptom | Cause | Action |
|---|---|---|---|
| B1 | Sohu article: 0 usable images | Body `data-src` is an obfuscated string | Do not decrypt. The page tail has a plaintext link list in body order — use that |
| B2 | WeChat article returns a 17 KB verification page, 0 images | URL truncated, missing `&chksm=...` | Copy the full URL from search results, including every query parameter; with the full URL the body is multi-MB |
| B3 | WeChat images 403 on download | Missing referer | `Referer: https://mp.weixin.qq.com/` on both page and image requests |
| B4 | WeChat body headings look like semantic labels but positions are wrong | JS escaping makes text-offset mapping unreliable | Use headings only as hints; **always confirm with visual frame picking** |
| B5 | Toutiao / Bilibili column: 0 images, tiny HTML | Images live in JS or behind an anti-bot page | Switch to a portal or curated gallery |
| B6 | `re.error: unterminated character set` | A character class ending in `\\` swallows the `]` | Use a safe class such as `[^\s"'<>]+?` |
| B7 | `json.decoder.JSONDecodeError: Invalid \escape` on Baidu `acjson` | Response contains illegal escapes | `json.loads(t, strict=False)` |
| B8 | Gallery page HTML has no full-size template | Site changed its markup | Inspect the page once, update the pattern; do not fabricate URLs |
| B9 | Article page returns 200 with 12 plaintext image URLs, but **every** image returns 403 | CDN hotlink policy; page reachability says nothing about the image host | Tried both the article URL and the site root as `Referer` (2026-11-06); both failed. **Switch source.** Do not keep varying headers |

## C. Image search semantic drift

| # | Symptom | Cause | Action |
|---|---|---|---|
| C1 | Chinese query returns 0 `murl` | Missing market parameter | Add `&mkt=zh-CN`. This fixed an earlier wrong conclusion that "Chinese is unsupported" |
| C2 | Query containing 截图 returns Excel screenshots and admin panels | The engine reads 截图 as "software screenshot" | Use 画面 / 剧照 / 观影截图 / 場面 / キャプチャ |
| C3 | `半熟男女 吵架 剧照` returns cats and a game character | Severe drift on Chinese film/TV queries | Do not rely on general image search for Chinese titles; use editorial articles |
| C4 | Anime line lookup returns only quote cards, fan art, logos, text infographics | No original frames indexed | Go to an editorial article covering that episode |
| C5 | English long query returns pandas | Semantic drift | Short queries with an explicit film title only |
| C6 | Baidu `acjson` works once, then every query returns 0 | Rate limiting / stricter validation | Switch source; do not burn time on cookie handling |
| C7 | Bing returns HTTP `000` in some environments | Host unreachable | `probe` detects it. Drop it for that run |
| C8 | 81 URLs / 70 downloaded images, all premiere photos and actor portraits | Search matched the film, not the scene | Visual re-check is mandatory; a high hit count is not a match |
| C9 | 10 URLs from a frame gallery, 9 downloaded, but 8 are title-logo frames, emoji and site mastheads | Naive URL extraction picks up decorative assets before the actual frames | Keep the dimension filter, then **look at the contact sheet**. A "9/10 valid" result can still contain zero usable stills |

## D. Download and engineering

| # | Symptom | Cause | Action |
|---|---|---|---|
| D1 | Serial download of 170+ images times out | No concurrency | `ThreadPoolExecutor(max_workers=10-12)`, 12-20 s per image |
| D2 | Gallery thumbnails 403 | Missing referer | `Referer: https://movie-screencaps.com/` |
| D3 | Thumbnail URL returns a full-size file / wrong variant | Missing `?class=thumbnail` | Keep the CDN size parameter |
| D4 | Full-size frames use a different host than thumbnails | `i0.wp.com/imgs.screencaps.us` mirror | Extract the template from the gallery page, do not hand-build it |
| D5 | `Tunnel connection failed: 502 Bad Gateway` on one page | Transient proxy | Retry **once**. If it fails again, switch source |
| D6 | `os.remove` raises and kills the batch | Some environments intercept file deletion | **Never delete in a script.** Validate in memory and only write valid bytes |
| D7 | Icons, avatars, ad banners mixed into candidates | Naive URL extraction | `Image.open(BytesIO(data))` + min-dimension check before writing |
| D8 | Guessed gallery slugs all 404 | In-site search is unreliable | External `site:` search, then use the exact URL |
| D9 | Frame-by-frame library has no page for a Netflix / arthouse title | Catalogue limited to commercial theatrical releases | Use a curated gallery or editorial article |
| D10 | `allscreencaps` returns HTML instead of an image for some films | Dead image objects | Validate content type and image header; skip the file |
| D11 | `Tunnel connection failed: 502 Bad Gateway` on an entire gallery, or on all its images | Network/proxy fault, not the site | One documented retry; if it still fails, switch source. Observed 2026-11-06 on two unrelated gallery hosts in the same session, while a third host worked |

## E. Image processing

| # | Symptom | Cause | Action |
|---|---|---|---|
| E1 | Solid black subtitle bar covers the actor's chin/forehead | Opaque band over the frame | Use a **gradient** darkening (alpha 0 -> 105) plus outlined text |
| E2 | Two subtitle layers stacked | Compositing without removing the original | Crop the original subtitle strip (~58 px) first |
| E3 | Viewing screenshot has subtitles + watermark; clean still needed | Platform capture | Crop bottom 95-100 px — both usually live there. Simpler and more reversible than inpainting |
| E4 | Contact sheet cells crop away subtitles | Forced uniform cell crop | Preserve aspect ratio and letterbox inside the cell |
| E5 | Adjacent numbered frames look identical | Gallery lists the same frame at 5-6 resolutions | Skip through the sheet; duplicates are normal, keep them anyway |
| E6 | Chinese text renders as boxes | No CJK font installed | Discover system fonts at runtime, or pass `--font` |
| E7 | Composited subtitle presented as a native frame | Missing annotation | Label it explicitly in the caption and manifest |

## F. Judgement errors

| # | Symptom | Cause | Action |
|---|---|---|---|
| F1 | Searched for a frame that does not exist | Trusted a widely repeated secondary summary | Fact-check first, see `fact-check.md` |
| F2 | Delivered a re-staged DVD cover photo as a film still | Iconic marketing image mistaken for a frame | Verify the image's provenance, not just its content |
| F3 | Picking a frame from filenames or text | Skipped the vision step | Always use a numbered contact sheet with a vision model or human |
| F4 | "First row, second column" mapped to the wrong file | Guessed from filesystem order | Resolve against the actual sheet layout and its labels |
| F5 | Two delivered images from the same film | No cross-check across picks | Check film diversity when delivering several images |
| F6 | Kept retrying a 403 host | No stop rule | One probe, record the status, switch source |

## Recording a new failure

Add one row with: date, exact error/status, host, likely cause, what you
switched to. State whether it was **solved**, **worked around**, or **judged
infeasible**. A dead host is useful information — do not delete old rows.
