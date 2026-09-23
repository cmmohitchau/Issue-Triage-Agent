"""Phase 2 job entry: approved artifact file -> GitHub writes (no LLM)."""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from issue_triage_agent.github_writes import GitHubWrites
from issue_triage_agent.phase2 import run_phase2
from issue_triage_agent.workflow import read_artifact_file


def default_make_writes() -> GitHubWrites:
    """Live GitHub writes factory (wired with the workflow GitHub token)."""
    raise RuntimeError("Live GitHub writes are not configured; refusing to write")


def main(
    argv: Sequence[str] | None = None,
    *,
    make_writes: Callable[[], GitHubWrites] = default_make_writes,
) -> int:
    """Apply the approved artifact; return 0, else 1 with no partial writes."""
    args = _parse_args(argv)
    try:
        artifact = read_artifact_file(args.artifact)
        run_phase2(artifact, args.issue_number, github=make_writes())
    except Exception as exc:
        print(f"phase 2 failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Triage phase 2: artifact to writes")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--issue-number", type=int, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
