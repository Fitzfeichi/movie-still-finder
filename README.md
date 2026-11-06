# movie-still-finder

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)
![License](https://img.shields.io/badge/License-MIT-blue)
![Version](https://img.shields.io/badge/Version-1.1.0-blue)
![No credentials](https://img.shields.io/badge/Credentials-none-brightgreen)

**Find a film still from a sentence.** An agent-agnostic [Agent Skill](https://agentskills.io)
that turns a scene description, a mood, or a line of dialogue into real, sourced,
visually verified image files — for article illustrations and covers.

[中文说明 / Chinese README](README.zh-CN.md)

```
"two people sitting in silence after an argument"
        -> fact-check -> source scouting -> 120 candidates
        -> numbered contact sheet -> vision model picks #22
        -> 1329x720 clean frame + manifest.json
```

No account. No API key. No browser login. No paid service. Python 3.9+ and
Pillow, nothing else. Works with Claude Code, Cursor, Codex, WorkBuddy, Gemini
CLI, or any agent that can read a `SKILL.md` and run a shell command.

## When to use this

Reach for this skill when you need a **real, sourced image** to illustrate
writing — not an AI-generated one:

- *"Find a movie still where two people sit in silence after an argument."*
- *"I need a film frame of a character saying X."* (台词 → 剧照；先核实台词是否真的存在)
- *"给这篇文章配一张剧照 / 封面"* (illustrate this paragraph with a film still or cover)
- *"Verify whether this quote actually appears in the film."*

---

## The problem

There is no free, public API that accepts a natural-language description and
returns the exact film frame — and almost certainly not one with the dialogue
subtitle burned in. Semantic-still services either require a paid subscription,
a signed request, or a login. Meanwhile the useful material is scattered across
curated frame galleries, frame-by-frame screenshot libraries, and editorial
articles whose captions are effectively human-labelled "scene -> image" data.

`movie-still-finder` does not pretend to be that missing API. It packages the **pipeline
that actually works**, including the unglamorous parts: dead hosts, Referer
headers, fact-checking misquoted lines, cropping burned-in subtitles, and
keeping every rejected candidate.

## What you get

| | |
|---|---|
| `SKILL.md` | The entry point any agent reads first. Progressive disclosure, no private paths. |
| `scripts/still.py` | One portable CLI: `probe`, `grab`, `sheet`, `quote`, `frames`, `full`, `crop`, `subtitle`, `deliver`, `rules`, `verify`. |
| `references/` | The distilled field notes: source priorities, ~30 recorded failure modes, fact-check cases, Pillow techniques, copyright boundary. |
| `profiles/` | Optional behaviour. Default is minimal; `editorial-wechat.json` opt-in bundles a human editor's workflow. |
| `tests/` | Offline end-to-end test on synthetic images + a portability/secrets scanner. No network, no copyrighted fixtures. |

## Install

```bash
# After cloning your own fork, or copying this folder into place:
cd movie-still-finder
python -m pip install -r requirements.txt
python scripts/still.py --help
```

To use it as a skill, place the folder in your agent's skills directory (for
example `~/.claude/skills/movie-still-finder/` or `.workbuddy/skills/movie-still-finder/`),
or simply point your agent at `SKILL.md`. No build step, no registration.

## 60-second example

Run `probe` first — source availability drifts, and a host that works today may
return 502 tomorrow. For a run that needs no network at all, see the offline
smoke test in [quickstart.md](examples/quickstart.md).

```bash
# 1. Which sources answer at all in this environment? (free, no login)
python scripts/still.py probe

# 2. Pull candidates from a gallery page verified reachable in the field run.
#    --image-referer is the site root; image CDNs rarely accept the article URL.
python scripts/still.py grab --out ./work \
  --page "https://movie-screencaps.com/avatar-2009/page/114" \
  --image-referer "https://movie-screencaps.com/" \
  --limit 40

# 3. Open ./work/contact_1.jpg with your eyes or a vision model; note the number
# 4. Prepare the winner and deliver with provenance
python scripts/still.py crop ./work/candidates/p1_02.jpg --bottom 100 -o ./work/clean.jpg
python scripts/still.py deliver ./work --picks examples/sample-picks.json --out ./delivery
```

`grab` writes `candidates/`, `contact_*.jpg`, and `manifest.json` (source page,
direct image URL, dimensions, timestamp). Nothing is deleted, ever. This
particular gallery page starts with title cards, so expect several decorative
frames in the sheet — that is exactly why the vision-picking step exists. A
`min_width` warning during delivery is also normal for thumbnail galleries:
use `full` to fetch the high-resolution original of the frame you picked.

Full walkthrough, including dialogue lookups and subtitle compositing:
[examples/quickstart.md](examples/quickstart.md).

## How it works

```
request
  |-- fact-check the line / scene ................ references/fact-check.md
  |-- probe source reachability ................. still.py probe
  |-- choose source by request type ............. references/sources.md
  |-- extract direct image URLs from pages
  |-- concurrent download, validate in memory, never write junk
  |-- numbered contact sheet .................... still.py sheet
  |-- VISION PICK (cannot be skipped)
  |-- high-res original / crop / subtitle ....... still.py full|crop|subtitle
  |-- visual re-check + provenance manifest
  `-- deliver ................................... still.py deliver
```

The vision step is the whole point. A text-only agent guessing from filenames
will pick the wrong frame; the contact sheet turns a search problem into a
multiple-choice question.

## Profiles

Default behaviour is deliberately small: general-purpose, no assumptions about
how you select images. Editorial preferences are **opt-in configuration**, not
baked-in policy.

```bash
python scripts/still.py rules --profile profiles/editorial-wechat.json
python scripts/still.py deliver ./work --picks picks.json \
  --profile profiles/editorial-wechat.json --out ./delivery
```

`editorial-wechat.json` enables: numbered previews with human selection (never
auto-finalize), dual-folder delivery that keeps **every** candidate, mandatory
fact-check, mandatory subtitle/source annotation, and a 2.35:1 cover-crop
comparison sheet. See [profiles/README.md](profiles/README.md).

## Repository layout

```
SKILL.md                  agent entry point
scripts/still.py          unified CLI
scripts/still_lib.py      fetch / extract / sheet / image ops / delivery
references/               field notes, read on demand
profiles/                 opt-in behaviour (JSON, standard library only)
examples/                 quickstart, sample request, sample picks manifest
tests/                    offline end-to-end + portability scanner
docs/iterations/          the three self-review rounds and their findings
```

## Design principles

1. **Credentials are a bug.** Anything requiring a login, a signing secret, or a
   paid plan is documented as an optional adapter, never a dependency.
2. **No private paths.** No usernames, no machine-specific Python interpreters,
   no absolute Windows paths, no project-local ledgers. `tests/test_portability.py`
   enforces this.
3. **Never delete a candidate.** "Rejected" means "not in the selected folder".
   The scanner fails if a script calls `os.remove` / `shutil.rmtree`.
4. **Provenance is part of the output.** An image without a source is not a
   deliverable.
5. **Composited subtitles are labelled.** Never pass an edited frame off as one
   from the film.
6. **Record dead ends.** Source availability changes; `references/pitfalls.md`
   is the accumulated memory of what stopped working and why.

## Sources (short version)

| Priority | Source | Good for |
|---|---|---|
| best | FilmGrab curated frame galleries | Clean, wide, subtitle-free frames for covers |
| best | Editorial articles with captioned stills | Scene/mood semantics; captions act as labels |
| good | Frame-by-frame screenshot libraries | Exact frame by number, commercial theatrical films |
| good | Public subtitle-seek endpoint | Line -> film + millisecond timestamp |
| fallback | General image search | Unstable, heavy semantic drift; always visually re-check |

Full parameters, required `Referer` headers, and the known-dead list:
[references/sources.md](references/sources.md) and
[references/pitfalls.md](references/pitfalls.md).

## Legal

This repository contains **no film stills**. The test fixtures are synthetic
images generated at runtime. Film frames are the property of their rights
holders; downloading them for personal study or drafting an article is not the
same as a licence to redistribute. Read
[references/delivery.md](references/delivery.md) before publishing anything.
The code is MIT licensed; the images it helps you find are not.

## Contributing

Source availability changes constantly. The most valuable contribution is a
recorded failure mode or a newly working source — see
[CONTRIBUTING.md](CONTRIBUTING.md). Run `python tests/test_offline.py` and
`python tests/test_portability.py` before opening a PR.

## License

[MIT](LICENSE)
