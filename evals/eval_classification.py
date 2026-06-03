# ABOUTME: Runs the classification eval against an injected LLMClient (stub by default).
# ABOUTME: CLI prints a Markdown report; importable run() returns metrics for the CI test.
from __future__ import annotations

import argparse
from pathlib import Path

from outreach_agent.classify import LLMClassifier
from outreach_agent.llm import RuleBasedStubLLM
from outreach_agent.protocols import LLMClient

from .framework import ClassificationMetrics, evaluate, load_golden, to_markdown

GOLDEN_PATH = Path(__file__).parent / "golden" / "classification.jsonl"


def run(llm: LLMClient | None = None) -> ClassificationMetrics:
    """Classify the golden set with ``llm`` (or the stub) and score the result."""
    rows = load_golden(GOLDEN_PATH)
    classifier = LLMClassifier(llm or RuleBasedStubLLM())
    predictions = classifier.classify([row.to_prospect() for row in rows])
    return evaluate(rows, predictions)


def _build_llm(live: bool) -> LLMClient:
    if not live:
        return RuleBasedStubLLM()
    from outreach_agent.config import load_config
    from outreach_agent.llm import ClaudeCliClient

    # Live runs go through the Claude CLI (subscription auth), no API key needed.
    return ClaudeCliClient(load_config())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the classification eval.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use the real Anthropic model instead of the deterministic stub.",
    )
    args = parser.parse_args()
    metrics = run(_build_llm(args.live))
    print(to_markdown(metrics))


if __name__ == "__main__":
    main()
