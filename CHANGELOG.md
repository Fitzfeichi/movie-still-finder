# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-11-07

Renamed the skill from `still-finder` to `movie-still-finder` and enriched the
metadata so agent directories and skill indexers can discover it more easily.

### Changed

- Renamed the skill and repository to `movie-still-finder` (the previous name
  lacked the core "movie/film" keyword that GitHub search and indexers key on).
- `SKILL.md` frontmatter: added `displayName`, `category`, and a `tags` list,
  and broadened the `description` trigger keywords.
- `README.md` / `README.zh-CN.md`: added status badges and a "When to use"
  section listing the trigger phrases.
- `README.md`: added a Mermaid pipeline diagram and a "Known limitations"
  section.

## [1.0.0] - 2026-11-06

First public release. Generalised from a four-round, single-machine field run
into an agent-agnostic skill.

### Added

- `SKILL.md` in the open Agent Skills format, with progressive disclosure and a
  request-type decision tree.
- Unified portable CLI `scripts/still.py`: `probe`, `grab`, `sheet`, `quote`,
  `frames`, `full`, `crop`, `subtitle`, `deliver`, `rules`, `verify`.
- `scripts/still_lib.py`: HTTP fetch with Referer handling, direct-URL
  extraction, in-memory image validation, numbered contact sheets,
  cross-platform font discovery, subtitle cropping/compositing, provenance
  manifest, dual-folder delivery.
- `references/`: end-to-end SOP, source priority table with required headers,
  accumulated failure modes, fact-check cases, image operations, delivery and
  copyright boundary, optional meme appendix, optional adapters.
- `profiles/minimal.json` (default) and `profiles/editorial-wechat.json`
  (opt-in human editor workflow). Credentials, provenance, and no-deletion are
  hard rules; profiles can only add constraints.
- Offline end-to-end test on synthetic fixtures and a portability/secret
  scanner, both runnable in CI without network access.
- Bilingual README, MIT licence, contributing guide, CI workflow.

### Design decisions

- No login, no API key, no paid service, no browser automation in the default
  path. Anything that needs them lives in `references/optional-adapters.md`.
- No film stills in the repository. Test images are generated at runtime.
- No absolute machine paths, usernames, or private ledger references anywhere.
- Scripts never delete files; rejected candidates are simply not selected.

Release notes beyond this point are generated from merged pull requests.
