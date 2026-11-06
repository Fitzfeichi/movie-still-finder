# -*- coding: utf-8 -*-
"""Portable building blocks for movie-still-finder.

Only the standard library and Pillow are used. No credentials, no machine
paths, no deletion. ``file://`` URLs are supported on purpose: they let the
offline test exercise the real download/extract pipeline without a network.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "profiles" / "minimal.json"
HARD_RULE_KEYS = ("source_manifest", "subtitle_annotation_required", "record_dead_ends")
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".gif")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# (label, probe URL, referer). Only public, login-free hosts.
PROBE_HOSTS = (
    ("film-grab", "https://film-grab.com/?s=Yi+Yi", None),
    ("movie-screencaps", "https://movie-screencaps.com/", "https://movie-screencaps.com/"),
    ("screencapsmovie", "https://www.screencapsmovie.com/", "https://www.screencapsmovie.com/"),
    ("zhaotaici", "https://zhaotaici.cn/", "https://zhaotaici.cn/"),
    ("sohu", "https://www.sohu.com/", None),
    ("weixin", "https://mp.weixin.qq.com/", "https://mp.weixin.qq.com/"),
    ("bing-images", "https://www.bing.com/images/search?q=film+still&mkt=en-US", None),
)

# Cross-platform font candidates. Nothing here contains a user directory.
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/msyh.ttc",
)

IMG_RE = re.compile(
    r'(?:[a-zA-Z][a-zA-Z0-9+.-]*:)?//[^\s"\'<>()\\]+?\.(?:jpg|jpeg|png|webp)'
    r'(?:\?[^\s"\'<>()\\]*)?', re.I)
QPIC_RE = re.compile(r'https?://mmbiz\.qpic\.cn/[^\s"\'<>()\\]+', re.I)


class FetchError(RuntimeError):
    """A source could not be read. A 403 is a decision to switch source."""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch(url: str, referer: str | None = None, timeout: float = 20,
          retries: int = 1, max_bytes: int | None = None) -> bytes:
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", None) or 200
                if status >= 400:
                    raise FetchError(f"HTTP {status} for {url}")
                return resp.read(max_bytes) if max_bytes else resp.read()
        except urllib.error.HTTPError as exc:
            # 403 / 404 / paywalls are not transient: fail immediately.
            raise FetchError(f"HTTP {exc.code} for {url}") from exc
        except FetchError:
            raise
        except Exception as exc:  # noqa: BLE001 - network errors are reported, not swallowed
            last = exc
            if attempt >= retries:
                break
    raise FetchError(f"{url}: {last}")


def probe(hosts=PROBE_HOSTS, timeout: float = 8) -> list[dict]:
    results = []
    for name, url, referer in hosts:
        try:
            data = fetch(url, referer=referer, timeout=timeout, retries=0, max_bytes=2048)
            results.append({"name": name, "url": url, "status": 200,
                            "bytes": len(data), "ok": True})
        except FetchError as exc:
            m = re.search(r"HTTP (\d+)", str(exc))
            results.append({"name": name, "url": url,
                            "status": int(m.group(1)) if m else 0,
                            "ok": False, "error": str(exc)})
    return results


def extract_image_urls(text: str, base: str) -> list[str]:
    """Extract direct image URLs from HTML, preserving document order."""
    text = html_mod.unescape(text).replace("\\/", "/").replace("\\u002F", "/")
    out: list[str] = []

    def add(raw: str) -> None:
        u = raw.strip().rstrip(");,.'\"\\")
        if u.startswith("//"):
            u = "https:" + u
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", u):
            u = urllib.parse.urljoin(base, u)
        if u not in out:
            out.append(u)

    for m in IMG_RE.finditer(text):
        add(m.group(0))
    for m in QPIC_RE.finditer(text):
        add(m.group(0))
    return out


def validate_image(data: bytes, min_width: int = 400,
                   min_height: int = 250) -> tuple[Image.Image, tuple[int, int]] | None:
    """Validate entirely in memory. Only valid bytes are ever written to disk."""
    try:
        im = Image.open(BytesIO(data))
        im.load()
        if im.width < min_width or im.height < min_height:
            return None
        # Pillow warns when a P-mode image carrying byte transparency is
        # converted straight to RGB; go through RGBA to keep CLI output clean.
        if im.mode == "P" and "transparency" in im.info:
            im = im.convert("RGBA")
        return im.convert("RGB"), (im.width, im.height)
    except Exception:  # noqa: BLE001 - a bad response is simply not a candidate
        return None


def download_jobs(jobs: list[dict], outdir: Path, workers: int = 10,
                  timeout: float = 20, min_width: int = 400,
                  min_height: int = 250) -> list[dict]:
    """Concurrent download with in-memory validation. Existing files are reused."""
    outdir.mkdir(parents=True, exist_ok=True)

    def one(job: dict) -> dict:
        dest = outdir / f"{job['id']}.jpg"
        if dest.is_file():
            try:
                cached = Image.open(dest)
                cached.load()
                return {**job, "ok": True, "file": dest.name,
                        "width": cached.width, "height": cached.height}
            except Exception:  # noqa: BLE001
                pass
        try:
            data = fetch(job["url"], referer=job.get("referer"),
                         timeout=timeout, retries=1)
        except FetchError as exc:
            return {**job, "ok": False, "error": str(exc)}
        checked = validate_image(data, min_width, min_height)
        if checked is None:
            return {**job, "ok": False, "error": "invalid image or below minimum size"}
        _, (w, h) = checked
        dest.write_bytes(data)
        return {**job, "ok": True, "file": dest.name, "width": w, "height": h}

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(one, jobs))


def contact_sheet(items: list[tuple[str, Image.Image]], outdir: Path,
                  prefix: str = "contact", cell: tuple[int, int] = (240, 150),
                  cols: int = 6, per: int = 42, label_h: int = 20) -> list[Path]:
    """Numbered sheets. Aspect ratio is preserved; nothing is cropped away."""
    outdir.mkdir(parents=True, exist_ok=True)
    W, H = cell
    paths: list[Path] = []
    for start in range(0, len(items), max(1, per)):
        chunk = items[start:start + per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * W, rows * (H + label_h)), (238, 238, 238))
        draw = ImageDraw.Draw(sheet)
        for k, (label, im) in enumerate(chunk):
            x, y = (k % cols) * W, (k // cols) * (H + label_h)
            thumb = im.convert("RGB")
            thumb.thumbnail((W, H))
            sheet.paste(thumb, (x + (W - thumb.width) // 2, y + (H - thumb.height) // 2))
            draw.text((x + 4, y + H + 2), str(label), fill=(10, 10, 10))
        p = outdir / f"{prefix}_{start // per + 1}.jpg"
        sheet.save(p, quality=88)
        paths.append(p)
    return paths


def load_font(size: int, font_path: str | None = None) -> ImageFont.FreeTypeFont:
    candidates = ([font_path] if font_path else []) + list(FONT_CANDIDATES)
    for path in candidates:
        if path and Path(path).is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:  # noqa: BLE001
                continue
    for name in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:  # noqa: BLE001
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def crop_bottom(im: Image.Image, px: int) -> Image.Image:
    return im.convert("RGB").crop((0, 0, im.width, max(1, im.height - px)))


def crop_ratio(im: Image.Image, ratio: float = 2.35,
               anchor: float = 0.42) -> Image.Image:
    im = im.convert("RGB")
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio)
        x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(w / ratio)
    y = int((h - nh) * anchor)
    return im.crop((0, y, w, min(h, y + nh)))


def _centered_text(draw: ImageDraw.ImageDraw, text: str, y: int, width: int,
                   font, size: int) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    x = (width - (box[2] - box[0])) // 2
    draw.text((x, y), text, font=font, fill=(255, 255, 255),
              stroke_width=max(1, size // 14), stroke_fill=(0, 0, 0))


def composite_subtitle(im: Image.Image, text: str, second_line: str | None = None,
                       font_path: str | None = None,
                       gradient: int = 105) -> Image.Image:
    """White outlined text over a bottom gradient. Never a solid black band."""
    base = im.convert("RGBA")
    W, H = base.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    band = max(1, int(H * 0.22))
    for y in range(H - band, H):
        od.line([(0, y), (W, y)],
                fill=(0, 0, 0, int(gradient * ((y - (H - band)) / band))))
    base = Image.alpha_composite(base, overlay).convert("RGB")
    draw = ImageDraw.Draw(base)
    size = max(24, int(W * 0.028))
    font = load_font(size, font_path)
    main_y = H - int(size * (3.0 if second_line else 2.0))
    _centered_text(draw, text, main_y, W, font, size)
    if second_line:
        small_size = max(14, int(size * 0.55))
        small = load_font(small_size, font_path)
        _centered_text(draw, second_line, H - int(size * 1.7), W, small, small_size)
    return base


def load_profile(path: str | Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_PROFILE
    if not p.is_absolute() and not p.is_file():
        p = ROOT / p
    data = json.loads(p.read_text(encoding="utf-8"))
    rules = data.get("rules")
    if not isinstance(rules, dict):
        raise ValueError(f"{p}: missing 'rules' object")
    for key in HARD_RULE_KEYS:
        if not rules.get(key):
            raise ValueError(f"{p}: hard rule {key!r} cannot be disabled")
    if rules.get("human_picks") and rules.get("auto_finalize"):
        raise ValueError(f"{p}: human_picks requires auto_finalize=false")
    return data


def write_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_candidate(cand_dir: Path, cid: str) -> Path | None:
    for suffix in IMAGE_SUFFIXES:
        p = cand_dir / f"{cid}{suffix}"
        if p.is_file():
            return p
    return None


def build_cover_compare(selected: list[tuple[Path, str]], cfg: dict, out: Path) -> Path:
    ratio = float(cfg.get("ratio", 2.35))
    anchor = float(cfg.get("anchor", 0.42))
    W = int(cfg.get("output_width", 900))
    H = int(W / ratio)
    bar, gap = 40, 12
    sheet = Image.new("RGB", (W, len(selected) * (H + bar + gap)), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    font = load_font(18)
    for i, (path, label) in enumerate(selected):
        y = i * (H + bar + gap)
        im = crop_ratio(Image.open(path), ratio, anchor).resize((W, H), Image.LANCZOS)
        sheet.paste(im, (0, y))
        draw.rectangle((0, y + H, W, y + H + bar), fill=(250, 250, 250))
        draw.text((10, y + H + 10), label[:110], font=font, fill=(25, 25, 25))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    return out


def deliver(work: Path, picks_path: Path, profile: dict, out: Path) -> dict:
    """Copy picks into a delivery. Every candidate is kept; nothing is removed."""
    work, out = Path(work), Path(out)
    rules = profile["rules"]
    picks_data = json.loads(Path(picks_path).read_text(encoding="utf-8"))
    work_manifest_path = work / "manifest.json"
    work_manifest = (json.loads(work_manifest_path.read_text(encoding="utf-8"))
                     if work_manifest_path.is_file() else {"items": [], "sources": []})
    by_id = {item["id"]: item for item in work_manifest.get("items", []) if item.get("ok")}
    cand_dir = work / "candidates"
    selected_dir = out / "selected"
    selected_dir.mkdir(parents=True, exist_ok=True)

    items, chosen_paths, warnings = [], [], []
    for pick in picks_data.get("picks", []):
        cid = str(pick["id"])
        src = _find_candidate(cand_dir, cid)
        if src is None:
            warnings.append(f"pick {cid!r} not found in {cand_dir}")
            continue
        name = pick.get("as") or src.name
        dst = selected_dir / name
        shutil.copy2(src, dst)
        src_meta = by_id.get(cid, {})
        with Image.open(dst) as im:
            w, h = im.size
        if w < int(rules.get("min_width", 0)):
            warnings.append(f"{name}: width {w}px is below min_width {rules.get('min_width')}")
        processed = pick.get("processed", "none")
        items.append({
            "id": cid,
            "file": f"selected/{name}",
            "source_page": src_meta.get("source_page", pick.get("source_page", "unknown")),
            "source_image": src_meta.get("url", pick.get("source_image", "unknown")),
            "film": pick.get("film", "unknown"),
            "width": w,
            "height": h,
            "processed": [processed] if isinstance(processed, str) else processed,
            "subtitle_composited": "subtitle" in str(processed).lower(),
            "note": pick.get("note", ""),
        })
        chosen_paths.append((dst, f"{name} | {pick.get('note', '')}"))

    all_count = 0
    if rules.get("keep_every_candidate") and cand_dir.is_dir():
        all_dir = out / "all-candidates"
        for f in sorted(cand_dir.iterdir()):
            if f.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            m = re.match(r"p(\d+)_", f.name)
            sub = all_dir / (f"source_{int(m.group(1)):02d}" if m else "other")
            sub.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, sub / f.name)
            all_count += 1

    cfg = rules.get("cover_crop_preview")
    compare = None
    if cfg and chosen_paths:
        compare = build_cover_compare(chosen_paths, cfg, out / "cover_compare.jpg")

    if rules.get("avoid_duplicate_films"):
        films = [i["film"] for i in items if i["film"] != "unknown"]
        if len(films) != len(set(films)):
            warnings.append("multiple picks come from the same film")

    manifest = {
        "generated_at": now_iso(),
        "profile": profile.get("name", "unknown"),
        "request": picks_data.get("request", ""),
        "layout": rules.get("deliver_layout", "single-folder"),
        "sources": work_manifest.get("sources", []),
        "items": items,
        "all_candidates_count": all_count,
        "cover_compare": compare.name if compare else None,
        "dead_ends": work_manifest.get("dead_ends", []),
        "warnings": warnings,
    }
    write_manifest(out / "manifest.json", manifest)
    return {"selected": len(items), "all_candidates": all_count,
            "warnings": warnings, "manifest": out / "manifest.json"}
