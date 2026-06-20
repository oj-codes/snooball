"""Read a subreddit list file, normalize names, drop comments, dedupe.

The normalization rules here are the part of Snooball most worth testing: a
quiet bug would silently skip or mangle entries. Export's txt output and join's
txt input share this format, so the round-trip is a natural property to hold.

Accepted per-line forms (all normalize to the bare lowercased name):
``foo``, ``r/foo``, ``/r/foo``, ``R/Foo``, ``r//foo``, ``foo/``, and full URLs
like ``https://www.reddit.com/r/foo/`` (any reddit subdomain). Blank lines and
lines starting with ``#`` are skipped. A non-blank line that yields no valid
name is logged at WARNING and skipped — never silently dropped.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from pathlib import Path

log = logging.getLogger(__name__)

# A URL scheme like ``https://`` at the start of the line.
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://")
# A reddit host (any subdomain: www., old., np., or none) at the start.
_HOST_RE = re.compile(r"^(?:[a-z0-9-]+\.)*reddit\.com")
# One or more leading ``r/`` prefixes, tolerating extra slashes (``r//foo``).
_PREFIX_RE = re.compile(r"^(?:r/+)+")
# A valid subreddit name once everything else has been stripped.
_VALID_RE = re.compile(r"^[a-z0-9_]+$")


def normalize_subreddit(raw: str) -> str | None:
    """Normalize one line to a bare lowercased subreddit name.

    Returns None for blank lines and ``#`` comments (intentional skips), and
    also for a non-blank line that yields no valid name (logged at WARNING).
    """
    line = raw.strip()
    if not line or line.startswith("#"):
        return None

    s = line.lower()
    s = _SCHEME_RE.sub("", s)
    s = _HOST_RE.sub("", s)
    s = s.lstrip("/")
    s = _PREFIX_RE.sub("", s)
    name = s.split("/", 1)[0].strip()

    if not _VALID_RE.match(name):
        log.warning("Skipping unparseable subreddit line: %r", line)
        return None
    return name


def parse_subreddits(lines: Iterable[str]) -> list[str]:
    """Normalize an iterable of raw lines into a deduped, ordered name list.

    Duplicates (case-insensitively, since names are lowercased) are dropped,
    keeping first-seen order so the output is stable and predictable.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in lines:
        name = normalize_subreddit(raw)
        if name is None or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def parse_subreddit_file(path: Path) -> list[str]:
    """Read a subreddit list file and return its normalized, deduped names."""
    text = path.read_text(encoding="utf-8")
    return parse_subreddits(text.splitlines())
