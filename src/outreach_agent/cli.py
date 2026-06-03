# ABOUTME: Command-line entry point. Stages and the eval runner are wired in as milestones land.
# ABOUTME: Kept thin on purpose: the CLI only parses args and delegates to the pipeline.
from __future__ import annotations

import typer

from . import __version__

app = typer.Typer(
    add_completion=False,
    help="Autonomous, safety-gated B2B cold-outreach agent.",
)


@app.command()
def version() -> None:
    """Print the package version."""
    print(__version__)


if __name__ == "__main__":
    app()
