"""Read the authenticated account's current subscriptions and write them out.

Read-only. This module never subscribes or otherwise mutates the account; it
only reads ``reddit.user.subreddits(limit=None)``. Fetching is kept separate
from formatting so the format/write logic is unit-testable without a live
Reddit connection.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import praw


@dataclass(frozen=True)
class SubInfo:
    """The per-subreddit fields we care about for a backup."""

    name: str
    title: str
    subscribers: int
    nsfw: bool


class ExportTargetExists(RuntimeError):
    """Raised when the output path already exists and ``--force`` was not given."""


def fetch_subscriptions(reddit: praw.Reddit) -> list[SubInfo]:
    """Read the authenticated account's current subscriptions (read-only)."""
    subs: list[SubInfo] = []
    for s in reddit.user.subreddits(limit=None):
        subs.append(
            SubInfo(
                name=s.display_name,
                title=s.title or "",
                subscribers=int(s.subscribers or 0),
                nsfw=bool(s.over18),
            )
        )
    return subs


def to_txt(subs: Iterable[SubInfo]) -> str:
    """Render subscriptions as plain text, one name per line.

    This is the exact format ``join`` consumes: bare subreddit names, no
    ``r/`` prefix. Names are de-duplicated and sorted case-insensitively so the
    output is deterministic and diff-friendly.
    """
    names = sorted({s.name for s in subs}, key=str.lower)
    if not names:
        return ""
    return "\n".join(names) + "\n"


def to_json(subs: Iterable[SubInfo], generated_at: str) -> str:
    """Render a richer backup: per-subreddit metadata plus a top-level timestamp.

    ``generated_at`` is passed in (rather than read from the clock here) to keep
    this function pure and testable.
    """
    payload = {
        "generated_at": generated_at,
        "subreddits": [
            {
                "display_name": s.name,
                "title": s.title,
                "subscribers": s.subscribers,
                "nsfw": s.nsfw,
            }
            for s in sorted(subs, key=lambda s: s.name.lower())
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_export(path: Path, content: str, *, force: bool) -> None:
    """Write ``content`` to ``path``, refusing to clobber unless ``force``.

    Raises:
        ExportTargetExists: if ``path`` exists and ``force`` is False.
    """
    if path.exists() and not force:
        raise ExportTargetExists(
            f"{path} already exists. Pass --force to overwrite it, "
            "or choose a different path. (A backup tool must not clobber silently.)"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
