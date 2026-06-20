# Snooball

A small, extensible CLI for managing subreddit subscriptions on a Reddit
account from a flat text file. v0 bulk-joins a list of subreddits on an
authenticated account and exports an account's current subscriptions to a file.

See `CLAUDE.md` for the full spec and guardrails.

## Setup

Requires Python 3.12+. This project uses [uv](https://docs.astral.sh/uv/).

```sh
uv sync                      # create the venv and install deps
cp .env.example .env         # then fill in your Reddit script-app credentials
```

To create credentials, go to https://www.reddit.com/prefs/apps on the target
account, create an app of type **script**, and collect the client ID and secret.

## Usage

```sh
uv run snooball whoami                       # confirm auth (temporary, Phase 1)
uv run snooball export data/backups/main.txt # back up current subscriptions
uv run snooball join data/subreddits.txt --dry-run
uv run snooball join data/subreddits.txt --limit 40
```

## Development

```sh
uv run pytest
uv run ruff check .
uv run mypy
```
