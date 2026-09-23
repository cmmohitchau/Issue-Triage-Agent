"""Write-boundary protocol phase 2 depends on (FakeGitHub and real clients satisfy it)."""

from typing import Protocol


class GitHubWrites(Protocol):
    """Write-only GitHub operations available to phase 2 (no LLM)."""

    def create_label_if_missing(self, name: str) -> None: ...

    def apply_labels(self, issue_number: int, labels: list[str]) -> None: ...

    def post_comment(self, issue_number: int, body: str) -> None: ...
