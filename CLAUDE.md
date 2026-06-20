# Snooball

A small, extensible CLI for managing subreddit subscriptions on a Reddit account from a flat text file. v0 does two things: bulk-join a list of subreddits on an authenticated account, and export an account's current subscriptions to a file. The architecture should leave clean room to grow into other subreddit-management actions later (leave, sync, prune).

## What this tool does (v0 scope)

1. **Join.** Read a newline-delimited list of subreddits from a text file and subscribe the authenticated account to each one. Idempotent, resumable, paced, safe to re-run.
2. **Export.** Read the authenticated account's current subscriptions and write them to a file. Read-only, no pacing concerns, runs fully independently of join. Doubles as a backup and as the input source for a join on a different account (back up one account, restore to another).

Anything beyond these two is out of scope for v0 but the code should not paint us into a corner.

## Hard requirements (join)

These are the things that matter. Hold the line on them.

- **Idempotent by diffing, not by trial.** Before joining anything, fetch the account's current subscriptions once via `reddit.user.subreddits(limit=None)`, build a set of names, and only attempt to subscribe to the subreddits that are missing. Do not naively call subscribe on every line. This keeps re-runs cheap and makes resumability free.
- **Resumable, and `--limit` advances on its own.** Because the diff drives everything, a `--limit N` run joins the next N unjoined subreddits and the run after that picks up where it stopped, with no edits to the input file. This is the mechanism that makes safe daily chunking a one-liner (see Operational notes). If a run dies partway, re-running just continues. No fragile state file required.
- **Paced with jitter.** PRAW already respects Reddit's rate-limit headers and will sleep when needed, so do not hand-roll rate-limit math. Separately, add a small randomized delay (default 1.0 to 3.0 seconds, configurable) between subscribe calls. This is about not tripping account-standing abuse heuristics on newer or low-karma accounts, and it is a real concern, not theater.
- **Tolerant input parsing.** One subreddit per line. Accept and normalize all of: `r/foo`, `/r/foo`, `foo`, full URLs like `https://www.reddit.com/r/foo/`, and trailing slashes. Strip whitespace. Skip blank lines and lines starting with `#` as comments. Deduplicate. Lowercase for comparison.
- **Fail soft, never abort the batch.** A single bad subreddit must not kill the run. Catch per-subreddit failures (private, banned, quarantined, nonexistent, forbidden), log them with the reason, and keep going. Print a summary at the end: joined, skipped-already-subscribed, failed-with-reasons.
- **Credentials never touch the repo.** All secrets come from a `.env` file loaded at runtime. Ship a `.env.example`. The real `.env` is gitignored.
- **Dry-run mode.** A `--dry-run` flag that does the full parse and diff and prints exactly what would be joined, without calling subscribe. This is the default thing a careful person runs first.

## Hard requirements (export)

- **Read-only.** Export must never write to the account. It only reads `reddit.user.subreddits(limit=None)`.
- **Round-trippable default.** Default output is a plain text file, one subreddit per line, in the exact format `join` consumes. Export from account A then `join` on account B must work with no hand-editing.
- **Optional rich format.** A `--format json` flag writes a fuller backup with per-subreddit metadata (display name, title, subscriber count, NSFW flag) plus a top-level timestamp. Plain text stays the default.
- **Never overwrite silently.** If the target path exists, refuse unless `--force` is passed, or write to a timestamped filename. Pick one and be consistent. A backup tool that clobbers the previous backup is a bug.

## Tech stack

- Python 3.12+
- [PRAW](https://praw.readthedocs.io/) for all Reddit interaction. It handles OAuth and rate limiting automatically.
- [Typer](https://typer.tiangolo.com/) for the CLI. Chosen over argparse specifically because this tool is meant to grow subcommands, and Typer makes adding them clean.
- `python-dotenv` for loading credentials.
- `rich` for the progress bar and the end-of-run summary table. Optional but nice for a bulk operation where you want to watch it move.

Pin versions in `pyproject.toml` with a console-script entry point so `snooball` is a real command after install.

## Reddit API setup (context for whoever runs this)

The tool authenticates as a single user via a Reddit "script" app. To create credentials: go to https://www.reddit.com/prefs/apps on the target account, create an app of type **script**, and collect the client ID and client secret. Authentication is username/password plus client ID/secret (the script-app flow), which is correct for a personal single-account tool.

Free tier is 100 queries per minute per OAuth client and requires OAuth. A subscribe-from-a-list job is nowhere near that ceiling, so API rate limits are not a design constraint here. Account standing is (see Operational notes).

Because export-then-join across two accounts is a supported workflow, the `.env` simply points at whichever account you want to operate as. To migrate, run export with account A's credentials, swap the `.env` to account B, run join.

`.env.example` should contain:

```
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USERNAME=
REDDIT_PASSWORD=
REDDIT_USER_AGENT=snooball/0.1 by u:YOUR_USERNAME
```

The user agent must be descriptive and include the operating account name. Reddit treats generic or empty user agents as a flag.

## CLI shape

```
snooball join <path>        Subscribe the authed account to every subreddit in <path>
  --dry-run                 Parse and diff and report, but do not subscribe
  --delay-min FLOAT         Min seconds between subscribes (default 1.0)
  --delay-max FLOAT         Max seconds between subscribes (default 3.0)
  --limit INT               Cap how many to join this run (drives daily chunking)

snooball export <path>      Write the authed account's current subscriptions to <path>
  --format [txt|json]       Output format (default txt, join-compatible)
  --force                   Overwrite <path> if it exists
```

Future subcommands to leave room for, do not build now: `leave <path>`, `sync <path>` (make subscriptions exactly match the file, joining and leaving as needed), `prune` (leave dead or banned subs). `join`, `export`, and a future `leave`/`sync` all share subreddit-resolution and the same client, so keep that shared logic in its own module from the start.

## Suggested layout

```
snooball/
  pyproject.toml
  README.md
  CLAUDE.md
  .env.example
  .gitignore
  data/
    subreddits.txt          # the user's input list lives here, gitignored
    backups/                # export output lands here, gitignored
  src/snooball/
    __init__.py
    cli.py                  # Typer app and command wiring
    client.py               # builds the authenticated PRAW Reddit instance from env
    parsing.py              # read file, normalize names, dedupe, strip comments
    subscribe.py            # diff current subs against target, join the gap, fail-soft
    export.py               # read current subs, write txt or json
    report.py               # rich summary table and per-failure reasons
  tests/
    test_parsing.py         # this is the part worth unit-testing hardest
```

`parsing.py` is the module that earns tests. The normalization rules (URL forms, prefixes, comments, dedupe) are exactly where a quiet bug would silently skip or mangle entries. Cover them. Note that export's txt output and join's txt input share this format, so the round-trip is a natural test case too.

## Coding conventions

- Type hints throughout. Run `ruff` and `mypy` clean.
- The PRAW client lives in one place (`client.py`) and is constructed from env. Nothing else reads `os.environ` directly.
- Log at INFO for normal progress and WARNING for per-subreddit failures. The user should be able to redirect output to a file and have a readable record of exactly what happened.
- No silent excepts. Every caught exception either gets logged with its reason or re-raised. A bare `except: pass` is a defect.

## Operational notes (read before the first big run)

The target join account is new (about 4 months old) and low-karma (~27). Reddit applies tighter per-user action limits to low-trust accounts, and a large burst of automated subscribes is the pattern that trips abuse heuristics. There is no published per-day subscribe cap, so the approach is empirical and conservative.

- **Do not run all ~910 in one shot.** Chunk with `--limit`. Because join diffs against current subscriptions, the same command run daily walks the list automatically: `snooball join data/subreddits.txt --limit 40`.
- **Ramp, do not flat-rate.** Start at 30 to 50 per day while the account is coldest, then push toward ~100/day after a week or two of normal-looking activity. Rough path to clearing 910 is about two weeks.
- **Warm the account in parallel.** Manual comments and posts raise karma and make the automated subscribes look like one activity among many.
- **Treat 429s and silent subscribe failures as a stop signal.** Back off, do not push through.
- These numbers are judgment, not Reddit policy. Tune down if anything looks off.

## Guardrails

- Do not build scraping, vote actions, comment automation, crossposting, or anything that acts on other users. This tool reads and curates one account's own subscriptions and nothing else. Keeping that boundary clean is also what keeps it firmly inside Reddit's API terms.
- Do not add proxy rotation, fake user agents, or anything that looks like evasion infrastructure. The pacing and jitter exist to respect account-standing limits, not to defeat them.
- Do not commit `.env`, `data/subreddits.txt`, `data/backups/`, or any logs containing account identifiers.

## Definition of done for v0

A user can run `snooball export data/backups/main.txt` against one account to capture its subscriptions, then point `.env` at a second account and run `snooball join data/backups/main.txt --dry-run` to preview, then join it in paced `--limit` chunks across several days. Re-running join does almost nothing because the diff sees everything is already subscribed. Export against the second account at the end captures the result as a recoverable backup.