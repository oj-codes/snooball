"""Typer app and command wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from snooball import export as export_mod
from snooball.client import MissingCredentialsError, build_reddit

app = typer.Typer(
    help="Manage subreddit subscriptions on a Reddit account from a flat text file.",
    no_args_is_help=True,
)
console = Console()


class ExportFormat(StrEnum):
    """Output formats for ``snooball export``."""

    txt = "txt"
    json = "json"


@app.callback()
def main() -> None:
    """Snooball — manage subreddit subscriptions from a flat text file."""
    # Present so Typer keeps a multi-command (subcommand) structure even while
    # only one command exists. Future commands (join, export) slot in cleanly.


@app.command()
def whoami() -> None:
    """Print the authenticated account's username.

    Temporary Phase-1 command to confirm auth works. Read-only.
    """
    try:
        reddit = build_reddit()
    except MissingCredentialsError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    me = reddit.user.me()
    if me is None:
        console.print(
            "[red]Authenticated, but reddit.user.me() returned None. "
            "Check that the credentials are for a script app and are valid.[/red]"
        )
        raise typer.Exit(code=1)

    console.print(f"Authenticated as [bold green]u/{me}[/bold green]")


@app.command()
def export(
    path: Annotated[
        Path,
        typer.Argument(
            help="Where to write the subscriptions (e.g. data/backups/main.txt)."
        ),
    ],
    fmt: Annotated[
        ExportFormat,
        typer.Option(
            "--format",
            help="Output format. txt is join-compatible; json adds metadata.",
        ),
    ] = ExportFormat.txt,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite the target file if it already exists."),
    ] = False,
) -> None:
    """Write the authenticated account's current subscriptions to PATH (read-only)."""
    try:
        reddit = build_reddit()
    except MissingCredentialsError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    subs = export_mod.fetch_subscriptions(reddit)

    if fmt is ExportFormat.json:
        generated_at = datetime.now(UTC).isoformat()
        content = export_mod.to_json(subs, generated_at)
    else:
        content = export_mod.to_txt(subs)

    try:
        export_mod.write_export(path, content, force=force)
    except export_mod.ExportTargetExists as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(
        f"Exported [bold green]{len(subs)}[/bold green] subscriptions "
        f"to [bold]{path}[/bold] ([cyan]{fmt.value}[/cyan])."
    )


if __name__ == "__main__":
    app()
