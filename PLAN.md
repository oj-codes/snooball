# PLAN.md

Build sequence for Snooball v0. This file is scaffolding. Delete it once v0 is done. Durable project facts live in CLAUDE.md, not here.

Work one phase at a time. Each phase ends at a STOP gate where a human verifies before the next phase starts. The only phase that writes to a Reddit account is the last one, and it is fenced behind a dry-run and a tiny smoke test.

## Phase 1: Scaffold and auth

- [ ] `pyproject.toml` with the stack from CLAUDE.md and a `snooball` console-script entry point
- [ ] Directory layout from CLAUDE.md, including empty modules
- [ ] `.env.example`, `.gitignore` (gitignore `.env`, `data/subreddits.txt`, `data/backups/`)
- [ ] `client.py` builds an authenticated PRAW instance from env, and nothing else reads env directly
- [ ] A temporary `snooball whoami` command (or equivalent) that prints `reddit.user.me()`

**STOP.** Human runs `whoami` against the main account and confirms it prints the username. Nothing proceeds until auth works.

## Phase 2: Export (read-only, do this before join)

- [ ] `export.py` reads `reddit.user.subreddits(limit=None)`
- [ ] `snooball export <path>` writes plain txt, one subreddit per line, in the exact format join consumes
- [ ] `--format json` writes the richer backup with metadata and a timestamp
- [ ] Refuses to overwrite an existing path unless `--force`

**STOP.** Human runs export against the main account, opens the file, confirms it looks right. This file becomes a test fixture for later phases.

## Phase 3: Parsing and its tests

- [ ] `parsing.py` normalizes `r/foo`, `/r/foo`, `foo`, full URLs, trailing slashes; strips whitespace; skips blanks and `#` comments; dedupes; lowercases for comparison
- [ ] `tests/test_parsing.py` covers every one of those rules
- [ ] Round-trip test: the txt that export wrote in Phase 2 parses back to the same set

**STOP.** Human runs `pytest`, `ruff`, `mypy`. All clean.

## Phase 4: Join, dry-run only

- [ ] `subscribe.py` fetches current subscriptions once, diffs against the parsed target, builds the join list from the gap
- [ ] Per-subreddit failures (private, banned, quarantined, nonexistent, forbidden) are caught, logged with reason, and do not abort the batch
- [ ] `report.py` prints the end summary: joined, skipped-already-subscribed, failed-with-reasons
- [ ] `snooball join <path> --dry-run` prints the full plan and calls subscribe zero times
- [ ] No real subscribe call exists in any code path yet except behind the not-dry-run branch, which is not exercised in this phase

**STOP.** Human runs `join --dry-run` against the new account with the full ~910-line list and confirms the planned count and the entries look correct. Still zero real subscribes.

## Phase 5: Pacing and the first real subscribes

- [ ] Randomized delay between subscribes (`--delay-min` / `--delay-max`, defaults 1.0 / 3.0)
- [ ] `--limit N` caps the run, and because of the Phase 4 diff it advances to the next unjoined batch on re-run
- [ ] Progress output during the run

**STOP.** Human runs `snooball join data/subreddits.txt --limit 5` against the new account. Watch all five go through. Confirm a second `--limit 5` run joins the *next* five, not the same five. Only after that smoke test passes is the tool trusted with paced daily chunks per the Operational notes in CLAUDE.md.

## Out of scope for v0

`leave`, `sync`, `prune`. Do not build them. Leave the shared client and subreddit-resolution code factored so they slot in cleanly later.
