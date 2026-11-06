#!/usr/bin/env python3
"""Offline end-to-end test of the real CLI, using synthetic file:// fixtures.

No network, no credentials, no copyrighted images. This is the test CI runs.

    python tests/test_offline.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "still.py"
FIXTURES = ROOT / "tests" / "_fixtures"
PASSED: list[str] = []


def run(*args, cwd: Path | None = None, expect: int = 0) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, str(CLI), *[str(a) for a in args]],
        cwd=str(cwd or ROOT), env=env, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=180)
    if proc.returncode != expect:
        print(f"FAIL command: {' '.join(str(a) for a in args)}")
        print(f"  expected exit {expect}, got {proc.returncode}")
        print("  stdout:\n" + proc.stdout)
        print("  stderr:\n" + proc.stderr)
        raise SystemExit(1)
    return proc


def check(condition: bool, label: str) -> None:
    if not condition:
        print(f"FAIL: {label}")
        raise SystemExit(1)
    PASSED.append(label)
    print(f"  ok  {label}")


def main() -> int:
    # 0. Generate synthetic fixtures through the shipped generator.
    gen = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "make_fixtures.py"),
         "--out", str(FIXTURES), "--count", "12"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check(gen.returncode == 0, "fixture generator runs standalone")
    page = (FIXTURES / "page.html")
    picks = FIXTURES / "picks.json"
    check(page.is_file() and picks.is_file(), "page.html and picks.json generated")
    check(len(list((FIXTURES / "images").glob("f*.jpg"))) == 12, "12 synthetic images")

    # 1. Environment + in-memory pipeline check.
    out = run("verify").stdout
    check("PASS: offline pipeline" in out, "CLI verify passes offline")

    # 2. Profiles are readable and the opt-in one is actually different.
    minimal = run("rules").stdout
    editorial = run("rules", "--profile", "profiles/editorial-wechat.json").stdout
    check("profile: minimal" in minimal, "default profile is minimal")
    check("dual-folder" in editorial and "single-folder" in minimal,
          "editorial profile changes delivery layout")
    check("hard rules" in editorial, "hard rules are surfaced to the agent")

    with tempfile.TemporaryDirectory(prefix="movie-still-finder-offline-") as tmp:
        tmp = Path(tmp)
        work, delivery_min, delivery_ed = tmp / "work", tmp / "delivery_min", tmp / "delivery_ed"

        # 3. Full pipeline against a local file:// page — the real grab command.
        run("grab", "--out", work, "--page", page.as_uri(),
            "--limit", "14", "--per", "6", "--cols", "3", "--workers", "4")
        candidates = work / "candidates"
        valid = sorted(candidates.glob("p1_*.jpg"))
        check(len(valid) == 12, "grab downloads 12 valid images")
        check(not (candidates / "p1_13.jpg").exists(),
              "broken image rejected in memory, never written")
        check((work / "contact_1.jpg").is_file() and (work / "contact_2.jpg").is_file(),
              "two numbered contact sheets generated")
        check((work / "page_1.html").is_file(), "raw HTML retained for re-extraction")
        manifest = json.loads((work / "manifest.json").read_text(encoding="utf-8"))
        check(manifest["downloaded"] == 12 and manifest["total"] == 13,
              "manifest counts match reality")
        check(all(i.get("source_page") and i.get("url") for i in manifest["items"]),
              "every candidate has provenance")
        check(any("invalid image" in str(i.get("error")) for i in manifest["items"]),
              "broken download recorded as a dead end")
        check(manifest["sheets"] == ["contact_1.jpg", "contact_2.jpg"],
              "sheets listed in manifest")

        # 4. Regenerating a sheet from an existing folder.
        run("sheet", candidates, "--per", "6", "--cols", "3", "--out", work)
        check((work / "contact_1.jpg").is_file(), "sheet regeneration works")

        # 5. Image operations.
        clean = work / "clean.jpg"
        run("crop", candidates / "p1_02.jpg", "--bottom", "100", "-o", clean)
        from PIL import Image  # local import: Pillow is already a dependency
        with Image.open(clean) as im:
            check(im.size == (1280, 620), "crop removes the 100px subtitle strip")
        sub = work / "subtitled.png"
        sub_out = run("subtitle", clean, "VERIFY SUBTITLE",
                      "--second-line", "SECOND LINE", "-o", sub).stdout
        check(sub.is_file(), "subtitle compositing writes a file")
        check("LABEL AS COMPOSITED" in sub_out, "composited subtitle is labelled in output")

        # 6. Default delivery: single folder + provenance.
        run("deliver", work, "--picks", picks, "--out", delivery_min)
        sel = list((delivery_min / "selected").glob("*.jpg"))
        check(len(sel) == 2, "minimal delivery contains the 2 picks")
        check(not (delivery_min / "all-candidates").exists(),
              "minimal profile does not build the full candidate folder")
        m = json.loads((delivery_min / "manifest.json").read_text(encoding="utf-8"))
        check(m["layout"] == "single-folder", "manifest records the layout")
        check(all(i["source_page"] != "unknown" and i["source_image"] != "unknown"
                  for i in m["items"]), "delivered items carry source page + image URL")
        check(m["items"][0]["subtitle_composited"] is False,
              "subtitle_composited flag is derived correctly")

        # 7. Opt-in profile: dual folder, zero deletion, cover comparison.
        # Deliberately use a RELATIVE profile path from another cwd to exercise
        # the repo-root fallback in load_profile().
        ed_out = run("deliver", work, "--picks", picks,
                     "--profile", "profiles/editorial-wechat.json",
                     "--out", delivery_ed, cwd=tmp).stdout
        allc = list((delivery_ed / "all-candidates").rglob("*.jpg"))
        check(len(allc) == 12, "editorial profile keeps EVERY candidate")
        check((delivery_ed / "cover_compare.jpg").is_file(),
              "2.35:1 cover comparison sheet built")
        m2 = json.loads((delivery_ed / "manifest.json").read_text(encoding="utf-8"))
        check(m2["layout"] == "dual-folder" and m2["all_candidates_count"] == 12,
              "dual-folder layout recorded with a count")
        check("human_picks is on" in ed_out, "human-in-the-loop rule is enforced in output")
        check(len(sorted(candidates.glob("*.jpg"))) == 12,
              "no source candidate was deleted by any command")

        # 8. Hard rules cannot be switched off by a custom profile.
        bad = tmp / "bad-profile.json"
        bad.write_text(json.dumps({
            "name": "bad", "rules": {
                "human_picks": False, "auto_finalize": True,
                "deliver_layout": "single-folder", "min_width": 1000,
                "source_manifest": False,
                "subtitle_annotation_required": True,
                "record_dead_ends": True}}), encoding="utf-8")
        bad_run = run("rules", "--profile", bad, expect=1)
        check("cannot be disabled" in bad_run.stderr,
              "profile that disables a hard rule is rejected")

    print(f"\nPASS: {len(PASSED)} offline end-to-end checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
