"""Tests for snooball.parsing — the normalization rules earn the hardest tests."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from snooball.export import SubInfo, to_txt
from snooball.parsing import (
    normalize_subreddit,
    parse_subreddit_file,
    parse_subreddits,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Bare name and prefixes
        ("foo", "foo"),
        ("r/foo", "foo"),
        ("/r/foo", "foo"),
        ("R/foo", "foo"),
        ("R/Foo", "foo"),
        # Lowercasing for comparison
        ("FOO", "foo"),
        ("BuyItForLife", "buyitforlife"),
        # Underscores and digits are valid name characters
        ("r/foo_bar", "foo_bar"),
        ("r/4chan", "4chan"),
        # Trailing slashes
        ("r/foo/", "foo"),
        ("/r/foo/", "foo"),
        # Stray double slashes (seen in the real input file)
        ("r//foo", "foo"),
        ("R//foo", "foo"),
        # Whitespace is stripped
        ("  r/foo  ", "foo"),
        ("\tr/foo\n", "foo"),
        # Full URL forms, any reddit subdomain, with/without trailing slash
        ("https://www.reddit.com/r/foo/", "foo"),
        ("https://www.reddit.com/r/Foo", "foo"),
        ("http://old.reddit.com/r/foo", "foo"),
        ("https://np.reddit.com/r/foo/", "foo"),
        ("www.reddit.com/r/foo", "foo"),
        ("reddit.com/r/foo", "foo"),
        # A URL with a trailing path/query keeps only the subreddit segment
        ("https://www.reddit.com/r/foo/comments/abc/title/", "foo"),
        ("https://www.reddit.com/r/foo/?utm_source=share", "foo"),
        # A bare name that merely starts with "r" must not be mangled
        ("rust", "rust"),
        ("redditdev", "redditdev"),
    ],
)
def test_normalize_valid_forms(raw: str, expected: str) -> None:
    assert normalize_subreddit(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "\t", "\n"])
def test_normalize_blank_returns_none(raw: str) -> None:
    assert normalize_subreddit(raw) is None


@pytest.mark.parametrize("raw", ["# comment", "#r/foo", "   # indented comment"])
def test_normalize_comments_returns_none(raw: str) -> None:
    assert normalize_subreddit(raw) is None


@pytest.mark.parametrize("raw", ["r/", "/r/", "!!!", "r/foo bar", "@@@"])
def test_normalize_unparseable_returns_none_and_warns(
    raw: str, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        assert normalize_subreddit(raw) is None
    # Not a silent skip: a warning is emitted for non-blank junk.
    assert any("unparseable" in rec.message.lower() for rec in caplog.records)


def test_parse_skips_blanks_and_comments() -> None:
    lines = [
        "# a header comment",
        "",
        "r/foo",
        "   ",
        "bar",
        "# trailing comment",
    ]
    assert parse_subreddits(lines) == ["foo", "bar"]


def test_parse_dedupes_case_insensitively_preserving_order() -> None:
    lines = ["r/foo", "R/FOO", "foo", "https://www.reddit.com/r/Foo/", "bar", "r/foo"]
    assert parse_subreddits(lines) == ["foo", "bar"]


def test_parse_file_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "subs.txt"
    path.write_text("r/foo\n# note\n\nR/Bar\nbaz\n", encoding="utf-8")
    assert parse_subreddit_file(path) == ["foo", "bar", "baz"]


def test_export_txt_round_trips_through_parse() -> None:
    """The txt export writes must parse back to the same (lowercased) name set.

    This is the load-bearing property: export from account A then join on
    account B has to work with no hand-editing.
    """
    subs = [
        SubInfo("BuyItForLife", "Buy It For Life", 1_200_000, False),
        SubInfo("askscience", "Ask Science", 25_000_000, False),
        SubInfo("programming", "Programming", 6_000_000, False),
    ]
    txt = to_txt(subs)
    parsed = parse_subreddits(txt.splitlines())
    assert set(parsed) == {s.name.lower() for s in subs}
    # No duplicates introduced by the round-trip.
    assert len(parsed) == len(set(parsed))
