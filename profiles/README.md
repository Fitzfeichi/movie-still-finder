# Profiles

Profiles control **behaviour preferences**, not compliance. They are plain JSON
(parsed with the standard library — no PyYAML, no extra dependency).

| Profile | Use it when |
|---|---|
| `minimal.json` (default) | You want a general-purpose pipeline that makes no assumptions about how images are chosen. |
| `editorial-wechat.json` | You are illustrating a Chinese long-form article and want a human editor's workflow: numbered previews, human selection, keep every candidate, mandatory fact-check, cover-crop comparison. |

```bash
# See exactly which rules are active before starting a run
python scripts/still.py rules
python scripts/still.py rules --profile profiles/editorial-wechat.json

# Apply a profile to a delivery
python scripts/still.py deliver ./work --picks picks.json \
  --profile profiles/editorial-wechat.json --out ./delivery
```

## Schema

```json
{
  "name": "my-profile",
  "description": "what this is for",
  "version": 1,
  "rules": { "...": "..." }
}
```

| Key | Type | Effect |
|---|---|---|
| `human_picks` | bool | Show a numbered preview and wait for the human to choose; never auto-finalize. |
| `auto_finalize` | bool | Whether the agent may decide the final image itself. Must be `false` when `human_picks` is `true`. |
| `preview_batch_size` | int | Suggested candidates per preview batch (6-12 works well). Advisory, not a hard cap. |
| `keep_every_candidate` | bool | `deliver` copies **all** downloaded candidates into the delivery, not just the picks. |
| `deliver_layout` | string | `single-folder` or `dual-folder` (`selected/` + `all-candidates/`). |
| `fact_check_required` | bool | Require a line/scene verification step before searching. |
| `source_manifest` | bool | **Hard rule.** Write provenance for every delivered image. |
| `subtitle_annotation_required` | bool | **Hard rule.** Label composited subtitles as such. |
| `record_dead_ends` | bool | **Hard rule.** Record unreachable hosts instead of silently retrying. |
| `cover_crop_preview` | object/null | `{"ratio": 2.35, "anchor": 0.42, "output_width": 900}` builds a comparison sheet. `anchor` is the vertical crop position (0 = top). |
| `min_width` | int | Minimum accepted width in pixels; the CLI warns on smaller images. |
| `avoid_duplicate_films` | bool | When delivering several images, warn if two come from the same film. |

## Hard rules

`load_profile()` in `scripts/still_lib.py` rejects any profile that sets a hard
rule to `false`. A profile can only **add** constraints, never remove these:

- Every delivered image has a provenance record (source page, direct URL, film,
  processing steps).
- Composited subtitles are labelled; a synthetic frame is never presented as one
  from the film.
- Dead hosts and workarounds are recorded.
- **No script in this repository deletes a file.** "Rejected" only means "not
  copied into `selected/`". The portability scanner fails on any `os.remove`,
  `os.unlink`, or `shutil.rmtree` call.

## Adding your own

```bash
cp profiles/minimal.json profiles/my-profile.json
# edit "rules", keep every hard rule true
python scripts/still.py rules --profile profiles/my-profile.json
```

If a preference needs new CLI behaviour, implement it as a `rules` key consumed
by `scripts/still.py`, and add an offline test — do not hard-code it into a
single command.
