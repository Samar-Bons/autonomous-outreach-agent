# ABOUTME: Command-line entry point. Wires the stages into a Pipeline and runs a demo.
# ABOUTME: Kept thin: the CLI parses args and composes components; logic lives in the stages.
from __future__ import annotations

import typer

from . import __version__
from .classify import ConstrainedAnglePicker, LLMClassifier
from .config import load_config
from .copy import TemplateCopyGenerator, TemplateStore
from .delivery import DryRunSender
from .enrich import SyntheticEmailFinder, SyntheticEmailVerifier
from .llm import AnthropicClient, RuleBasedStubLLM
from .pipeline import Pipeline
from .protocols import LLMClient
from .safety import InMemorySuppressionStore, default_gate
from .schedule import SystemClock, WarmupWavePlanner
from .sources import DEFAULT_SEED_PATH, CsvDataSource

app = typer.Typer(
    add_completion=False,
    help="Autonomous, safety-gated B2B cold-outreach agent.",
)


@app.command()
def version() -> None:
    """Print the package version."""
    print(__version__)


@app.command(name="run-demo")
def run_demo(
    live: bool = typer.Option(False, help="Use the real model instead of the stub."),
) -> None:
    """Run the full pipeline on the synthetic seed data and print the funnel."""
    config = load_config()
    llm: LLMClient = AnthropicClient(config) if live else RuleBasedStubLLM()

    pipeline = Pipeline(
        source=CsvDataSource(DEFAULT_SEED_PATH),
        classifier=LLMClassifier(llm),
        angle_picker=ConstrainedAnglePicker(llm),
        email_finder=SyntheticEmailFinder(),
        email_verifier=SyntheticEmailVerifier(),
        copy_generator=TemplateCopyGenerator(TemplateStore()),
        gate=default_gate(),
        suppression=InMemorySuppressionStore(),
        planner=WarmupWavePlanner(SystemClock(), campaign=config.campaign),
        sender=DryRunSender(),
    )
    result = pipeline.run()

    print(f"prospects sourced:   {result.total_prospects}")
    print(f"quarantined:         {result.quarantined}")
    print(f"no angle / no email: {result.no_angle} / {result.no_email}")
    print(f"suppressed (skipped): {result.suppressed_skipped}")
    print(f"drafts generated:    {result.drafts_generated}")
    print(f"drafts blocked:      {result.drafts_blocked}")
    print(f"scheduled / sent:    {result.scheduled} / {result.sent}")


if __name__ == "__main__":
    app()
