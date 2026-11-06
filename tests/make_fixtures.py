#!/usr/bin/env python3
"""Generate synthetic, copyright-free fixtures for the offline test.

Produces coloured numbered images, one deliberately broken file, a local HTML
page referencing them via file:// URLs, and a sample picks manifest. The
offline test then runs the REAL grab/sheet/crop/subtitle/deliver CLI against it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "tests" / "_fixtures"
PALETTE = [(72, 96, 128), (128, 84, 72), (84, 118, 84), (112, 92, 132),
           (140, 124, 72), (72, 122, 132), (132, 80, 104), (96, 112, 72),
           (104, 88, 140), (140, 100, 72), (72, 116, 96), (120, 120, 120)]


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def build(out: Path, count: int = 12) -> dict:
    out = Path(out)
    images = out / "images"
    images.mkdir(parents=True, exist_ok=True)
    big, small = _font(170), _font(28)

    for n in range(1, count + 1):
        colour = PALETTE[(n - 1) % len(PALETTE)]
        im = Image.new("RGB", (1280, 720), colour)
        d = ImageDraw.Draw(im)
        d.rectangle((80 + (n % 4) * 40, 80, 560 + (n % 4) * 40, 480),
                    outline=(240, 240, 240), width=8)
        d.text((640, 200), f"{n:02d}", font=big, fill=(250, 250, 250))
        d.text((640, 420), f"SYNTHETIC FRAME {n:02d}", font=small, fill=(235, 235, 235))
        # Simulated burned-in subtitle + watermark strip.
        d.rectangle((0, 620, 1280, 720), fill=(18, 18, 18))
        d.text((470, 645), f"SIMULATED SUBTITLE {n:02d}", font=small, fill=(245, 245, 245))
        d.text((1130, 645), "WM", font=small, fill=(200, 200, 200))
        im.save(images / f"f{n:03d}.jpg", quality=88)

    # Intentionally not an image: exercises in-memory validation.
    (images / "broken.png").write_text("this is not an image", encoding="utf-8")

    refs = [(images / f"f{n:03d}.jpg").as_uri() for n in range(1, count + 1)]
    refs.append((images / "broken.png").as_uri())
    body = "\n".join(f'<p><img src="{u}"></p>' for u in refs)
    (out / "page.html").write_text(
        "<!doctype html><html><body>\n" + body + "\n</body></html>\n", encoding="utf-8")

    picks = {
        "request": "offline end-to-end verification",
        "profile_hint": "editorial-wechat",
        "picks": [
            {"id": "p1_02", "as": "01_frame_two.jpg",
             "film": "Synthetic Frame A (2026)",
             "note": "second numbered cell", "processed": "none"},
            {"id": "p1_07", "as": "02_frame_seven.jpg",
             "film": "Synthetic Frame B (2026)",
             "note": "seventh numbered cell",
             "processed": "cropped 100px bottom"},
        ],
    }
    (out / "picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    return {"images": count, "broken": 1, "page": str(out / "page.html"),
            "picks": str(out / "picks.json")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic offline fixtures")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--count", type=int, default=12)
    a = ap.parse_args(argv)
    info = build(Path(a.out), a.count)
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
