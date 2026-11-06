#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""movie-still-finder CLI — find, prepare and deliver sourced film stills.

    python scripts/still.py --help
    python scripts/still.py probe
    python scripts/still.py grab --out ./work --page <url> --limit 40
    python scripts/still.py deliver ./work --picks picks.json --out ./delivery

No credentials, no machine-specific paths. Only Pillow is required.
See SKILL.md and references/ for the workflow around these commands.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import urllib.parse
from pathlib import Path

from PIL import Image

try:
    import still_lib as lib
except ImportError:  # allow `python -m scripts.still` from the repo root
    from scripts import still_lib as lib

QUOTE_API = "https://zhaotaici.cn/php/api/subtitle_seek_api.php"
MS_BASE = "https://movie-screencaps.com"


def _origin(url: str) -> str:
    """Site root, which is what image CDNs usually expect as Referer."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    return ""


def _open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as im:
        return im.convert("RGB")


def _load_sheet_items(directory: Path) -> list[tuple[str, Image.Image]]:
    items = []
    for f in sorted(directory.iterdir()):
        if f.suffix.lower() in lib.IMAGE_SUFFIXES and not f.name.startswith("contact"):
            try:
                items.append((f.stem, _open_rgb(f)))
            except Exception:  # noqa: BLE001 - one bad file should not break the sheet
                print(f"[warn] unreadable image: {f.name}", file=sys.stderr)
    return items


def cmd_probe(a) -> int:
    hosts = list(lib.PROBE_HOSTS)
    for extra in a.host or []:
        hosts.append((extra, extra, None))
    results = lib.probe(hosts, timeout=a.timeout)
    print(f"{'source':<20} {'status':<8} {'bytes':<8} result")
    for r in results:
        status = r["status"] or "ERR"
        size = r.get("bytes", "-")
        note = "ok" if r["ok"] else r.get("error", "unreachable")
        print(f"{r['name']:<20} {str(status):<8} {str(size):<8} {note[:90]}")
    dead = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(dead)}/{len(results)} reachable. "
          "A 403 means switch source, not retry.")
    if a.json:
        lib.write_manifest(Path(a.json), {"generated_at": lib.now_iso(), "results": results})
        print(f"[probe] wrote {a.json}")
    return 0


def cmd_grab(a) -> int:
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    profile = lib.load_profile(a.profile)
    sources, jobs, dead_ends = [], [], []
    remaining = a.limit

    for i, page in enumerate(a.page, 1):
        if remaining is not None and remaining <= 0:
            break
        referer = a.referer or page
        # Page requests use the page URL; image CDNs usually want the site root.
        image_referer = a.image_referer or _origin(page) or referer
        try:
            data = lib.fetch(page, referer=referer, timeout=a.timeout, retries=1)
            (out / f"page_{i}.html").write_bytes(data)
            urls = lib.extract_image_urls(data.decode("utf-8", "ignore"), page)
            if remaining is not None:
                urls = urls[:remaining]
                remaining -= len(urls)
            sources.append({"index": i, "page": page, "status": 200,
                            "urls_found": len(urls), "fetched_at": lib.now_iso()})
            print(f"[page {i}] {len(urls)} image URLs from {page[:90]}")
            for j, url in enumerate(urls, 1):
                jobs.append({"id": f"p{i}_{j:02d}", "url": url,
                             "source_page": page, "source_index": i,
                             "referer": image_referer})
        except lib.FetchError as exc:
            dead_ends.append({"page": page, "error": str(exc), "action": "skipped / switched source"})
            print(f"[page {i}] FAIL {page[:90]}: {exc}", file=sys.stderr)

    if not jobs:
        print("No image URLs found. Check the page, Referer, or try another source "
              "(see references/sources.md).", file=sys.stderr)
        lib.write_manifest(out / "manifest.json", {
            "generated_at": lib.now_iso(), "profile": profile.get("name"),
            "sources": sources, "items": [], "sheets": [], "dead_ends": dead_ends})
        return 1

    cand = out / "candidates"
    results = lib.download_jobs(jobs, cand, workers=a.workers, timeout=a.timeout,
                                min_width=a.min_width, min_height=a.min_height)
    items = []
    for r in results:
        item = {"id": r["id"], "url": r["url"], "source_page": r["source_page"],
                "source_index": r["source_index"], "ok": r["ok"]}
        item.update({k: r[k] for k in ("file", "width", "height", "error") if k in r})
        items.append(item)

    ok = [r for r in results if r["ok"]]
    sheets = []
    if ok:
        sheet_items = [(r["id"], _open_rgb(cand / r["file"])) for r in ok]
        sheets = lib.contact_sheet(sheet_items, out, per=a.per, cols=a.cols)
    lib.write_manifest(out / "manifest.json", {
        "generated_at": lib.now_iso(),
        "profile": profile.get("name"),
        "sources": sources,
        "items": items,
        "sheets": [p.name for p in sheets],
        "downloaded": len(ok),
        "total": len(jobs),
        "dead_ends": dead_ends,
    })
    print(f"[grab] {len(ok)}/{len(jobs)} valid images -> {cand}")
    for p in sheets:
        print(f"[sheet] {p}")
    print(f"[manifest] {out / 'manifest.json'}")
    if dead_ends:
        print(f"[dead ends] {len(dead_ends)} recorded; see manifest.json")
    print("Next: open the contact sheet with a vision model, note the number.")
    return 0 if ok else 1


def cmd_sheet(a) -> int:
    directory = Path(a.dir).resolve()
    outdir = Path(a.out).resolve() if a.out else directory
    items = _load_sheet_items(directory)
    if not items:
        print(f"No images found in {directory}", file=sys.stderr)
        return 1
    paths = lib.contact_sheet(items, outdir, per=a.per, cols=a.cols)
    for p in paths:
        print(f"[sheet] {p}")
    print(f"[sheet] {len(items)} images")
    return 0


def cmd_quote(a) -> int:
    is_en = 0 if re.search(r"[\u4e00-\u9fff]", a.query) else 1
    params = {
        "action": "seek_all", "search_type": "text",
        "query": a.query.replace(" ", "_"), "pageNum": a.page,
        "title_filter": a.title, "tag_filter": "", "actor_filter": "",
        "area_filter": "", "year_filter": "", "director_filter": "",
        "is_en": is_en,
    }
    url = QUOTE_API + "?" + urllib.parse.urlencode(params)
    try:
        data = lib.fetch(url, referer="https://zhaotaici.cn/", timeout=a.timeout)
    except lib.FetchError as exc:
        print(f"[quote] source unavailable: {exc}", file=sys.stderr)
        print("Do not retry in a loop. Verify the line another way and switch source.",
              file=sys.stderr)
        return 1
    payload = json.loads(data.decode("utf-8", "ignore"))
    hits = payload.get("items") or []
    print(f"pages={payload.get('pageTotal')}  is_en={is_en}  hits={len(hits)}")
    for it in hits[:a.limit]:
        title = (it.get("subTableItem") or {}).get("title", "")
        sentence = it.get("sentence") or {}
        sub = sentence.get("json_sub_item") or {}
        print(f"  sub_id={sentence.get('sub_id')} start_ms={sub.get('start')} "
              f"[{title[:34]}] zh={str(sub.get('zh', ''))[:44]!r} "
              f"en={str(sub.get('en', ''))[:44]!r}")
    print("Fact-check the line before searching for a frame (references/fact-check.md).")
    if a.json:
        lib.write_manifest(Path(a.json), {"query": a.query, "title": a.title,
                                          "is_en": is_en, "items": hits[:a.limit]})
    return 0


def _ms_page(slug: str, page: int, timeout: float) -> str:
    return lib.fetch(f"{MS_BASE}/{slug}/page/{page}",
                     referer=MS_BASE + "/", timeout=timeout).decode("utf-8", "ignore")


def cmd_frames(a) -> int:
    try:
        text = _ms_page(a.slug, a.page, a.timeout)
    except lib.FetchError as exc:
        print(f"[frames] {exc}", file=sys.stderr)
        return 1
    nums = sorted({int(n) for n in re.findall(
        r"caps2\.b-cdn\.net/[^\"'\s<>]*?-(\d+)\.jpg", text)})
    m = re.search(r'(https://caps2\.b-cdn\.net/[^\s"\'<>]*?)-\d+\.jpg', text)
    if not nums or not m:
        print("No frame template found; the gallery markup may have changed. "
              "Check references/sources.md.", file=sys.stderr)
        return 1
    gallery = f"{MS_BASE}/{a.slug}/page/{a.page}"
    tmpl = m.group(1) + "-{}.jpg?class=thumbnail"
    jobs = [{"id": str(n), "url": tmpl.format(n), "source_page": gallery,
             "referer": MS_BASE + "/"} for n in nums]
    out = Path(a.out).resolve()
    results = lib.download_jobs(jobs, out / "candidates", workers=a.workers,
                                timeout=a.timeout, min_width=a.min_width,
                                min_height=a.min_height)
    ok = [r for r in results if r["ok"]]
    print(f"[frames] page {a.page}: {len(nums)} frame numbers, {len(ok)} downloaded")
    if ok:
        items = [(r["id"], _open_rgb(out / "candidates" / r["file"])) for r in ok]
        for p in lib.contact_sheet(items, out, per=a.per, cols=a.cols):
            print(f"[sheet] {p}")
    lib.write_manifest(out / "manifest.json", {
        "generated_at": lib.now_iso(), "source_page": gallery,
        "items": results, "sheets": [], "dead_ends": []})
    return 0 if ok else 1


def cmd_full(a) -> int:
    try:
        text = _ms_page(a.slug, a.page, a.timeout)
    except lib.FetchError as exc:
        print(f"[full] {exc}", file=sys.stderr)
        return 1
    m = re.search(r'(https://i0\.wp\.com/imgs\.screencaps\.us/[^\s"\'<>]*?)-\d+\.jpg\?ssl=1', text)
    if not m:
        print("Full-size template not found on the gallery page.", file=sys.stderr)
        return 1
    url = m.group(1) + f"-{a.number}.jpg?ssl=1"
    try:
        data = lib.fetch(url, referer=MS_BASE + "/", timeout=a.timeout)
    except lib.FetchError as exc:
        print(f"[full] {exc}", file=sys.stderr)
        return 1
    if lib.validate_image(data, 1000, 500) is None:
        print("[full] response is not a valid high-resolution image", file=sys.stderr)
        return 1
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"full_{a.number}.jpg"
    dest.write_bytes(data)
    with Image.open(dest) as im:
        print(f"[full] {dest} {im.size}  {url}")
    return 0


def cmd_crop(a) -> int:
    src = Path(a.image)
    if not src.is_file():
        print(f"No such image: {src}", file=sys.stderr)
        return 1
    dest = Path(a.output) if a.output else src.with_name(src.stem + "_clean.jpg")
    result = lib.crop_bottom(_open_rgb(src), a.bottom)
    dest.parent.mkdir(parents=True, exist_ok=True)
    result.save(dest, quality=92)
    print(f"[crop] {dest} {result.size} (removed {a.bottom}px from bottom)")
    print("Re-open it visually: some films place subtitles higher.")
    return 0


def cmd_subtitle(a) -> int:
    src = Path(a.image)
    if not src.is_file():
        print(f"No such image: {src}", file=sys.stderr)
        return 1
    dest = Path(a.output) if a.output else src.with_name(src.stem + "_subtitled.png")
    result = lib.composite_subtitle(_open_rgb(src), a.text,
                                    second_line=a.second_line, font_path=a.font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    result.save(dest)
    print(f"[subtitle] {dest} {result.size}")
    print("LABEL AS COMPOSITED: this subtitle is not present in the original frame.")
    if a.note:
        print(f"[note] {a.note}")
    print('Record it in picks.json, e.g. "processed": "subtitle composited".')
    return 0


def cmd_deliver(a) -> int:
    profile = lib.load_profile(a.profile)
    work = Path(a.work)
    if not work.is_dir():
        print(f"No such workspace: {work}", file=sys.stderr)
        return 1
    result = lib.deliver(work, Path(a.picks), profile, Path(a.out))
    print(f"[deliver] {result['selected']} selected -> {Path(a.out).resolve()}")
    if result["all_candidates"]:
        print(f"[deliver] all {result['all_candidates']} candidates kept in all-candidates/")
    else:
        print(f"[deliver] candidates are untouched in {work / 'candidates'} "
              "(minimal profile does not copy them; nothing was deleted)")
    print(f"[manifest] {result['manifest']}")
    for warning in result["warnings"]:
        print(f"[warn] {warning}", file=sys.stderr)
    if profile["rules"].get("human_picks"):
        print("human_picks is on: do not auto-finalize. Wait for the human's number.")
    return 0


def cmd_rules(a) -> int:
    profile = lib.load_profile(a.profile)
    print(f"profile: {profile.get('name')}  ({profile.get('description', '')[:80]})")
    for key, value in profile["rules"].items():
        print(f"  {key:<30} {json.dumps(value, ensure_ascii=False)}")
    print("\nhard rules (cannot be disabled): " + ", ".join(lib.HARD_RULE_KEYS))
    print("plus: no file deletion, no invented URLs, provenance on every delivery")
    return 0


def cmd_verify(a) -> int:
    """Offline environment + pipeline check. Never touches the network."""
    print(f"Pillow: {__import__('PIL').__version__}")
    font = lib.load_font(28)
    print(f"font: {getattr(font, 'path', 'built-in') or 'built-in'}")
    for name in ("minimal", "editorial-wechat"):
        profile = lib.load_profile(lib.ROOT / "profiles" / f"{name}.json")
        print(f"profile {name}: ok ({profile['rules']['deliver_layout']})")
    with tempfile.TemporaryDirectory(prefix="movie-still-finder-verify-") as tmp:
        root = Path(tmp)
        im = Image.new("RGB", (640, 360), (70, 90, 120))
        for n in range(3):
            shifted = Image.new("RGB", (640, 360), (70 + n * 30, 90, 120))
            shifted.save(root / f"f{n}.jpg", quality=85)
        sheets = lib.contact_sheet([(f"f{n}", im) for n in range(3)], root, per=2)
        assert len(sheets) == 2, "contact sheet pagination failed"
        assert lib.crop_bottom(im, 100).size == (640, 260), "crop failed"
        assert lib.crop_ratio(im, 2.35, 0.42).height < 360, "ratio crop failed"
        sub = lib.composite_subtitle(im, "verify", second_line="確認")
        assert sub.size == (640, 360), "subtitle compositing failed"
        urls = lib.extract_image_urls(
            '<img src="https://example.com/a.jpg"><img data-src="https://mmbiz.qpic.cn/x">',
            "https://example.com/")
        assert len(urls) == 2, "URL extraction failed"
    print("PASS: offline pipeline (extraction, sheet, crop, subtitle, profiles)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="still.py",
        description="Find, prepare and deliver sourced film stills. No login, no keys.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="check which public sources are reachable")
    p.add_argument("--host", action="append", help="extra URL to probe (repeatable)")
    p.add_argument("--timeout", type=float, default=8)
    p.add_argument("--json", help="write results to a JSON file")
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("grab", help="extract + download candidates from page(s)")
    p.add_argument("--out", required=True, help="workspace directory")
    p.add_argument("--page", action="append", required=True, help="page URL (repeatable)")
    p.add_argument("--limit", type=int, default=40, help="max image URLs, default 40")
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--timeout", type=float, default=20)
    p.add_argument("--referer", help="override Referer for page requests")
    p.add_argument("--image-referer",
                   help="override Referer for image CDN requests (default: site root)")
    p.add_argument("--min-width", type=int, default=400)
    p.add_argument("--min-height", type=int, default=250)
    p.add_argument("--per", type=int, default=42, help="cells per contact sheet")
    p.add_argument("--cols", type=int, default=6)
    p.add_argument("--profile", default=None)
    p.set_defaults(func=cmd_grab)

    p = sub.add_parser("sheet", help="regenerate numbered contact sheet(s) from a folder")
    p.add_argument("dir")
    p.add_argument("--out", default=None)
    p.add_argument("--per", type=int, default=42)
    p.add_argument("--cols", type=int, default=6)
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("quote", help="line -> film + millisecond timestamp")
    p.add_argument("query")
    p.add_argument("--title", default="")
    p.add_argument("--page", type=int, default=0)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--timeout", type=float, default=20)
    p.add_argument("--json", default=None)
    p.set_defaults(func=cmd_quote)

    p = sub.add_parser("frames", help="frame-by-frame gallery thumbnails + sheet")
    p.add_argument("slug")
    p.add_argument("page", type=int)
    p.add_argument("--out", default="out")
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--timeout", type=float, default=20)
    p.add_argument("--min-width", type=int, default=400)
    p.add_argument("--min-height", type=int, default=250)
    p.add_argument("--per", type=int, default=42)
    p.add_argument("--cols", type=int, default=6)
    p.set_defaults(func=cmd_frames)

    p = sub.add_parser("full", help="download one high-resolution frame by number")
    p.add_argument("slug")
    p.add_argument("page", type=int)
    p.add_argument("number", type=int)
    p.add_argument("--out", default="out")
    p.add_argument("--timeout", type=float, default=30)
    p.set_defaults(func=cmd_full)

    p = sub.add_parser("crop", help="remove burned-in subtitles / watermark at bottom")
    p.add_argument("image")
    p.add_argument("--bottom", type=int, default=100)
    p.add_argument("-o", "--output", default=None)
    p.set_defaults(func=cmd_crop)

    p = sub.add_parser("subtitle", help="composite a labelled subtitle onto a frame")
    p.add_argument("image")
    p.add_argument("text")
    p.add_argument("-o", "--output", default=None)
    p.add_argument("--second-line", default=None)
    p.add_argument("--font", default=None, help="path to a TTF/TTC font (CJK)")
    p.add_argument("--note", default=None)
    p.set_defaults(func=cmd_subtitle)

    p = sub.add_parser("deliver", help="copy picks + provenance; never delete candidates")
    p.add_argument("work")
    p.add_argument("--picks", required=True)
    p.add_argument("--out", default="delivery")
    p.add_argument("--profile", default=None)
    p.set_defaults(func=cmd_deliver)

    p = sub.add_parser("rules", help="show the active profile's rules")
    p.add_argument("--profile", default=None)
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("verify", help="offline environment + pipeline check")
    p.set_defaults(func=cmd_verify)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args) or 0)
    except (ValueError, OSError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
