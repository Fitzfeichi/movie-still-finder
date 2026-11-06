# Contributing

The most valuable contribution here is not code. It is a **recorded source
change**: a host that started returning 403, a parameter that stopped working,
or a new gallery that reliably serves clean frames. These expire constantly.

## Before opening a PR

```bash
python -m pip install -r requirements.txt
python tests/test_offline.py        # end-to-end on synthetic images, no network
python tests/test_portability.py   # hard-coded paths / secrets / deletion scan
python scripts/still.py --help
```

Both tests must pass. CI runs them on Python 3.9, 3.11 and 3.12 on Linux;
please do not assume Windows-only behaviour or a machine-specific interpreter.

## What belongs in a contribution

**Welcome**

- `references/sources.md`: a newly verified source, with the exact URL pattern,
  required headers, and the date you verified it.
- `references/pitfalls.md`: a failure mode, the exact error, its likely cause,
  and what you switched to. Include the date and your environment.
- `references/fact-check.md`: a widely repeated claim about a film that turned
  out to be wrong, with evidence.
- Portability fixes: font discovery, path handling, encoding, timeouts.
- New optional profiles, as long as they only **add** constraints.

**Not welcome**

- Real film stills, screenshots, or any copyrighted image asset. Test fixtures
  must be generated with `tests/make_fixtures.py`.
- Credentials, tokens, personal names, absolute home-directory paths, or
  machine-specific interpreter paths. The portability scanner will fail.
- Bypassing a login, a paywall, a signature, or anti-bot protection. If a host
  says 403, record it and switch sources instead.
- Code that deletes candidates, calls `os.remove` / `shutil.rmtree`, or
  "cleans up" intermediate directories.
- Auto-selecting a final image on the user's behalf when a human-in-the-loop
  profile is active.

## Adding a data source

1. Verify it with `python scripts/still.py probe` or a single `curl -I`, and
   record the HTTP status and date.
2. Add one row to the priority table in `references/sources.md` with: what it
   provides, URL pattern, required `Referer` / query parameters, known limits.
3. If it fails, add it to `references/pitfalls.md` instead. Do not quietly
   delete the old row — a dead host is useful information.
4. If the source needs a script change, add or update an offline test that does
   not depend on that host being reachable.

## Writing style

- `SKILL.md` stays short. Put detail in `references/` and link to it from the
  index table; agents have limited context.
- README and skill instructions are English-first, with
  `README.zh-CN.md` as the full Chinese counterpart. Chinese search-query
  templates stay in Chinese — they are data, not prose.
- State facts with a date. "Host X returns 403" is only useful with "as of
  2026-11-06".

## Licence

By contributing you agree that your contributions are licensed under MIT.
This covers code and documentation only, never the images a user finds.
