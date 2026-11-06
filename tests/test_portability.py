#!/usr/bin/env python3
"""Static quality gate: structure, frontmatter, links, profiles, secrets, deletion.

Runs entirely offline with the standard library. This repository is meant to be
dropped into any agent's skills directory, so three things are non-negotiable:
no machine-specific paths, no credentials, and no file deletion.

    python tests/test_portability.py
    python tests/test_portability.py --full     # also require scripts/ + tests/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".toml", ".cfg"}
SCAN_EXCLUDE_DIRS = {".git", "__pycache__", "tests", ".venv", "venv", "work", "out"}

# Iteration reports quote fixed findings verbatim (including placeholder
# strings), so placeholder scanning would be a false positive there. Private
# paths and credentials are still scanned in those files.
SOFT_SCAN_DIRS = {"iterations"}

# Anything tied to one person's machine, project, or a private ledger must not
# ship in a public, agent-agnostic skill.
PRIVATE_PATTERNS = [
    (r"C:\\Users\\", "Windows user directory"),
    (r"/Users/[A-Za-z0-9_.-]+/", "macOS user directory"),
    (r"E:\\00 MYSELF", "private workspace path"),
    (r"07 自媒体", "private project name"),
    (r"\.workbuddy[/\\]binaries", "machine-specific interpreter path"),
    (r"%APPDATA%", "Windows per-user config path"),
    (r"\b34304\b", "local username / id"),
    (r"\bAGENTS\.md\b", "private project rule file"),
    (r"配图反馈记录|排版反馈记录|文章配图流程|剧照检索技术档案", "private ledger / SOP name"),
    (r"\bstill-research\b", "private working directory name"),
    (r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}", "possible hard-coded credential"),
]

# Placeholders are fine in a template, not in a finished release.
PLACEHOLDER_PATTERNS = [
    (r"your-account|your-fork-url|<your-", "unresolved repository placeholder"),
    (r"git clone <", "install command still contains a placeholder"),
    (r"\bTODO\b|\bFIXME\b|\bXXX\b", "unfinished marker"),
]

DELETION_PATTERNS = [
    r"\bos\.remove\b", r"\bos\.unlink\b", r"\bshutil\.rmtree\b",
    r"\brmtree\s*\(", r"rm\s+-rf",
]

CORE_FILES = [
    "SKILL.md", "README.md", "README.zh-CN.md", "LICENSE", "CONTRIBUTING.md",
    "CHANGELOG.md", "requirements.txt", ".gitignore",
    ".github/workflows/ci.yml",
    "profiles/README.md", "profiles/minimal.json", "profiles/editorial-wechat.json",
    "examples/quickstart.md", "examples/sample-request.md", "examples/sample-picks.json",
    "references/workflow.md", "references/sources.md", "references/pitfalls.md",
    "references/image-ops.md", "references/fact-check.md", "references/delivery.md",
    "references/meme-optional.md", "references/optional-adapters.md",
]

FULL_MODE_FILES = [
    "scripts/still.py", "scripts/still_lib.py",
    "tests/make_fixtures.py", "tests/test_offline.py", "tests/test_portability.py",
]

HARD_RULE_KEYS = ("source_manifest", "subtitle_annotation_required", "record_dead_ends")

results: list[tuple[str, str]] = []


def fail(check: str, detail: str) -> None:
    results.append((check, detail))


def iter_product_files():
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SCAN_EXCLUDE_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.suffix.lower() in SCAN_SUFFIXES or p.name == ".gitignore":
            yield p


def check_structure(full: bool) -> None:
    for rel in CORE_FILES + (FULL_MODE_FILES if full else []):
        if not (ROOT / rel).is_file():
            fail("structure", f"missing required file: {rel}")


def check_frontmatter() -> None:
    p = ROOT / "SKILL.md"
    if not p.is_file():
        fail("frontmatter", "SKILL.md missing")
        return
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("frontmatter", "SKILL.md must start with a YAML frontmatter block")
        return
    end = text.find("\n---", 4)
    if end < 0:
        fail("frontmatter", "frontmatter block is not closed")
        return
    block = text[4:end]
    name = re.search(r"^name:\s*(\S+)\s*$", block, re.M)
    desc = re.search(r"^description:\s*(.+)$", block, re.M)
    if not name:
        fail("frontmatter", "missing 'name'")
    elif not re.fullmatch(r"[a-z0-9-]{1,64}", name.group(1)):
        fail("frontmatter", f"name must be lowercase kebab-case <=64 chars: {name.group(1)!r}")
    if not desc:
        fail("frontmatter", "missing 'description'")
    body = text[end + 4:]
    # 'description' is a folded scalar; estimate its length from the block.
    m = re.search(r"^description:\s*>-?\s*\n((?:  .*\n)+)", block, re.M)
    desc_text = " ".join(line.strip() for line in m.group(1).splitlines()) if m else (desc.group(1) if desc else "")
    if len(desc_text) > 1024:
        fail("frontmatter", f"description too long ({len(desc_text)} chars, limit 1024)")
    if len(body.splitlines()) > 250:
        fail("frontmatter", f"SKILL.md body is {len(body.splitlines())} lines; keep it short and use references/")
    for ref in ("references/workflow.md", "references/sources.md", "profiles/"):
        if ref not in body:
            fail("frontmatter", f"SKILL.md does not point to {ref}")


def check_links() -> None:
    link_re = re.compile(r"\]\(([^)]+)\)")
    for p in ROOT.rglob("*.md"):
        if any(part in SCAN_EXCLUDE_DIRS for part in p.relative_to(ROOT).parts):
            continue
        for target in link_re.findall(p.read_text(encoding="utf-8")):
            target = target.strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0]
            if not clean:
                continue
            resolved = (p.parent / clean).resolve()
            if not resolved.exists():
                fail("links", f"{p.relative_to(ROOT)} -> {target} (target does not exist)")


def check_private_and_placeholders() -> None:
    for p in iter_product_files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = p.relative_to(ROOT).as_posix()
        soft = any(part in SOFT_SCAN_DIRS for part in p.relative_to(ROOT).parts)
        patterns = PRIVATE_PATTERNS + ([] if soft else PLACEHOLDER_PATTERNS)
        for pattern, label in patterns:
            for m in re.finditer(pattern, text):
                line = text.count("\n", 0, m.start()) + 1
                fail("privacy", f"{rel}:{line} -> {label}: {m.group(0)!r}")


def check_no_deletion() -> None:
    scripts = ROOT / "scripts"
    if not scripts.is_dir():
        return  # R1: scripts land in round 2
    for p in scripts.glob("*.py"):
        text = p.read_text(encoding="utf-8")
        for pattern in DELETION_PATTERNS:
            for m in re.finditer(pattern, text):
                line = text.count("\n", 0, m.start()) + 1
                fail("deletion", f"{p.name}:{line} -> deletion call {m.group(0)!r}")


def check_profiles() -> None:
    for p in sorted((ROOT / "profiles").glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            fail("profiles", f"{p.name}: invalid JSON: {e}")
            continue
        rules = data.get("rules")
        if not isinstance(rules, dict):
            fail("profiles", f"{p.name}: missing 'rules' object")
            continue
        for key in HARD_RULE_KEYS:
            if not rules.get(key):
                fail("profiles", f"{p.name}: hard rule {key!r} cannot be disabled")
        if rules.get("human_picks") and rules.get("auto_finalize"):
            fail("profiles", f"{p.name}: human_picks requires auto_finalize=false")
        if rules.get("deliver_layout") not in ("single-folder", "dual-folder"):
            fail("profiles", f"{p.name}: invalid deliver_layout")
        if not isinstance(rules.get("min_width"), int):
            fail("profiles", f"{p.name}: min_width must be an integer")


def check_no_binary_images() -> None:
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in image_suffixes:
            if any(part in {"tests", "work", "out"} for part in p.relative_to(ROOT).parts):
                continue  # generated fixtures live under tests/ and are ignored
            fail("assets", f"repository must not ship real imagery: {p.relative_to(ROOT)}")


def check_ci_references(full: bool) -> None:
    if not full:
        return
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for rel in ("tests/test_offline.py", "tests/test_portability.py", "scripts/still.py"):
        if rel not in ci:
            fail("ci", f"CI does not exercise {rel}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Static portability/privacy gate")
    ap.add_argument("--full", action="store_true", help="also require scripts/, tests/ and CI references")
    args = ap.parse_args()

    check_structure(args.full)
    check_frontmatter()
    check_links()
    check_private_and_placeholders()
    check_no_deletion()
    check_profiles()
    check_no_binary_images()
    check_ci_references(args.full)

    if results:
        print(f"FAIL: {len(results)} issue(s) found\n")
        for check, detail in results:
            print(f"  [{check}] {detail}")
        print("\nFix the issues above, then re-run.")
        return 1
    mode = "full" if args.full else "static"
    print(f"PASS: {mode} portability checks (structure, frontmatter, links, "
          "privacy, no-deletion, profiles, no binary assets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
