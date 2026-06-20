"""Build the authenticated PRAW client from environment.

This is the *only* module that reads credentials from the environment.
Everything else takes a ``praw.Reddit`` instance as an argument.
"""

from __future__ import annotations

import os

import praw
from dotenv import load_dotenv

# The env vars that make up the script-app (username/password) OAuth flow.
_REQUIRED_VARS = (
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME",
    "REDDIT_PASSWORD",
    "REDDIT_USER_AGENT",
)


class MissingCredentialsError(RuntimeError):
    """Raised when one or more required credentials are absent from the env."""


def _load_env() -> dict[str, str]:
    """Load ``.env`` and return the required credential values.

    Raises:
        MissingCredentialsError: if any required variable is unset or blank.
    """
    load_dotenv()
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in _REQUIRED_VARS:
        value = os.environ.get(name, "").strip()
        if not value:
            missing.append(name)
        else:
            values[name] = value
    if missing:
        raise MissingCredentialsError(
            "Missing required credential(s): "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill it in."
        )
    return values


def build_reddit() -> praw.Reddit:
    """Construct an authenticated, read/write PRAW ``Reddit`` instance.

    PRAW handles OAuth and rate-limit header compliance itself. We only
    feed it credentials from the environment.
    """
    env = _load_env()
    return praw.Reddit(
        client_id=env["REDDIT_CLIENT_ID"],
        client_secret=env["REDDIT_CLIENT_SECRET"],
        username=env["REDDIT_USERNAME"],
        password=env["REDDIT_PASSWORD"],
        user_agent=env["REDDIT_USER_AGENT"],
    )
