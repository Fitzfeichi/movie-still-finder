# Image operations

All operations live in `scripts/still_lib.py` and are exposed through
`scripts/still.py`. Only Pillow is required. Nothing is deleted; outputs are
always new files.

## Principles

1. **Validate in memory, then write.** `Image.open(BytesIO(data))`, check format
   and minimum dimensions, then write the bytes. This avoids leaving icons and
   error pages on disk and means no cleanup code is ever needed.
2. **Preserve the original.** `crop` / `subtitle` / `deliver` write new files.
   The candidate stays untouched, so any decision is reversible.
3. **Keep aspect ratio in previews.** Never crop a cell to fit a grid — subtitles
   and faces get cut. Letterbox inside the cell instead.

## Numbered contact sheet — `grab` / `sheet`

```
cells:      200-300 px wide, aspect preserved
per sheet:  42-70 cells (long single images are hard to read)
label:      number printed under each cell, matching the candidate id
background: light neutral
```

The number is the contract between the sheet and the pick list. `grab` writes
`contact_1.jpg`, `contact_2.jpg`, ... and `manifest.json` maps each id to its
source. `sheet <dir>` regenerates sheets from an existing candidate directory.

Show the sheet to a **vision-capable model** or the human. Do not ask a text-only
model to infer content from `p1_07.jpg`.

## Cropping burned-in subtitles — `crop`

```
python scripts/still.py crop in.jpg --bottom 100 -o clean.jpg
```

- 95-100 px from the bottom removes the subtitle strip **and** the usual
  bottom-right platform watermark in one reversible step.
- Use ~58 px when you only need to clear the original subtitle before
  compositing a new one.
- Always re-open the result visually: some films place subtitles higher.

## Compositing a subtitle — `subtitle`

```
python scripts/still.py subtitle frame.jpg "I see you" -o out.png \
  --note "subtitle composited, not native"
```

- White bold text, ~`0.028 * width` px, 3 px black outline.
- Bottom **gradient** darkening (alpha 0 -> 105), never a solid black band:
  a solid band covers chins and foreheads.
- Optional two-line form for bilingual captions: main line larger, second line
  about half the size, both centred.
- Font discovery is cross-platform. The CLI searches common system font paths
  on Windows, macOS and Linux and falls back to Pillow's default font. Pass
  `--font /path/to/font.ttf` for CJK or a specific look.
- **Always label the result as composited** in the manifest and the delivery
  text. It is a derived image, not a frame from the film.

## Cover crop comparison — `deliver` (profile-driven)

When `cover_crop_preview` is set in the active profile, `deliver` builds a
vertical comparison sheet of all picks cropped to the target ratio.

```
ratio: 2.35, anchor: 0.42, output_width: 900
```

`anchor` is the vertical crop position (0 = keep the top, 1 = keep the bottom).
0.42 keeps heads in frame for wide material. Near-square source images need a
smaller anchor (~0.22) to preserve sky/headroom. Each pick can override the
anchor in the picks manifest.

The comparison sheet is for choosing, not for delivering: pick the crop you
like, then produce the final file from the original.

## Provenance fields

`manifest.json` records, per image: candidate id, source page, direct image URL,
download timestamp, pixel dimensions, film/year (when known), processing steps,
and whether any subtitle was composited. See `delivery.md`.

## Font discovery

| OS | Typical paths |
|---|---|
| Windows | `C:\Windows\Fonts\arialbd.ttf`, `segoeuib.ttf`, `msyh.ttc` (CJK) |
| macOS | `/System/Library/Fonts/Supplemental/Arial Bold.ttf`, `/Library/Fonts/Arial Unicode.ttf` |
| Linux | `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`, `.../noto/NotoSansCJK-Regular.ttc` |

`still_lib.load_font()` tries a list of candidates plus `PIL`'s bundled DejaVu,
then falls back to `ImageFont.load_default()`. A missing font is a warning,
never a crash — but CJK glyphs may render as boxes, so pass `--font` when
compositing Chinese subtitles.
