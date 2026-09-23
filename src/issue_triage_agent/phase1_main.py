"""Phase 1 job entry: issue event -> proposal artifact file (no writes exist)."""

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from issue_triage_agent.github_reads import GitHubReads
from issue_triage_agent.phase1 import run_phase1
from issue_triage_agent.workflow import payload_from_event, write_artifact_file


def default_make_llm() -> BaseChatModel:
    """Live model factory (wired by provider configuration)."""
    raise RuntimeError("Live LLM is not configured; refusing to triage")


def default_make_reads() -> GitHubReads:
    """Live GitHub reads factory (wired with the workflow GitHub token)."""
    raise RuntimeError("Live GitHub reads are not configured; refusing to triage")


def main(
    argv: Sequence[str] | None = None,
    *,
    make_llm: Callable[[], BaseChatModel] = default_make_llm,
    make_reads: Callable[[], GitHubReads] = default_make_reads,
) -> int:
    """Run phase 1; return 0 with the artifact file written, else 1 with none."""
    args = _parse_args(argv)
    try:
        event = json.loads(args.event_path.read_text(encoding="utf-8"))
        payload = payload_from_event(event)
        artifact = run_phase1(payload, llm=make_llm(), github=make_reads())
        write_artifact_file(args.out, artifact)
    except Exception as exc:
        print(f"phase 1 failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Triage phase 1: event to artifact")
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
