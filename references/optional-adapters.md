# Optional adapters (not dependencies)

The default pipeline needs nothing but Python and Pillow. This file describes
stronger tools you **may** add locally. Adding one is your decision; nothing in
`SKILL.md`, the CLI or CI requires any of them.

## Policy

1. An adapter must be able to fail without breaking the main pipeline.
2. Never commit credentials, tokens, config directories, browser profiles,
   machine-specific ports or absolute home paths.
3. Authorisation is always performed by the human, in the tool's own UI.
   This skill never logs in on the user's behalf or handles a password.
4. Record the adapter version and the date you verified it. Field names and
   endpoints change.
5. Respect the adapter's own licence. An AGPL-licensed service does not become
   MIT because a small client in this repo is MIT — keep them clearly separate.

## A. Local semantic frame search (VideoSeek-like)

If you have local video files and are willing to build an index, a local
semantic search engine is the closest thing to the "one sentence -> exact frame"
dream: CLIP-style visual search, OCR of burned-in subtitles for dialogue search,
and timestamp-based frame extraction, with a localhost API made for agents.

Typical shape (verify against the project's own `docs/for-agents.md` before use):

```
GET  /health                    -> index_ready
GET  /agent-starter             -> starter_text (the maintainer's binding guidance)
GET  /videos, /libraries        -> authoritative local paths
POST /search                    -> {"query", "query_type":"text",
                                   "search_kind":"visual|dialogue|tags",
                                   "top_k", "mode":"chunk"}
POST /frames/extract            -> {"video_path", "time_sec", "max_edge"}
                                   -> image_base64
POST /frames/extract/batch      -> up to 16 timestamps
```

Hard-won rules from reading that API's docs:

- Read `/agent-starter` first; it is the maintainer's declared binding strategy.
  Do not invent request shapes from a summary.
- `video_path` must come from `/videos`, `/libraries` or `hits[].video_path`.
  Never construct a path by string concatenation.
- The service is localhost-only and unauthenticated; do not expose it.
- For a quoted line, `search_kind:"dialogue"` -> best hit -> extract the frame
  at `start_sec + ~1s`.

**Reality check:** this path needs a real video library and a completed index.
With no local footage, use the public-source pipeline in `workflow.md`. A
previous field run wrote an adapter for this API but could not test it because
no footage was available — treat it as a documented option, not a verified path.

## B. CLI services with an account (meme libraries, etc.)

Some tools provide a quota-based search CLI after a browser authorisation.
If you adopt one:

- Keep the credential in the tool's own user config directory. Never copy it
  into the repository, a manifest, a log or a chat message.
- Do not use flags that print the key.
- Check `whoami`-style account status before assuming the saved login is valid.
- Free quotas and reset dates are snapshots; read the current account page.
- If authorisation fails with a filesystem permission error, diagnose the
  failure stage first. Do not repeatedly ask the human to log in, and do not
  widen permissions without a clear reason.

## C. Browser automation / logged-in platforms

Some sites only yield results through a logged-in browser session. This skill
does not automate logins, does not store browser profiles, and does not bypass
anti-bot checks. If your agent has its own browser capability, that capability
belongs to your environment — keep its profile directory and debugging port in
your own configuration, outside this repository.

A 403 from such a site is a **switch source** signal, recorded in the run log.

## When an adapter is worth it

| Situation | Recommendation |
|---|---|
| One article, a handful of stills | Default pipeline. Fast, reproducible, no setup. |
| You own a large local film library and search it repeatedly | Local semantic index. |
| You need exact frames at known timestamps across many films | Local index, or a frame library. |
| You need memes from a commercial library | Optional CLI adapter, with the human's authorisation. |

Adapters are additive. The acceptance checklist in `workflow.md` still applies
to any image they produce.
