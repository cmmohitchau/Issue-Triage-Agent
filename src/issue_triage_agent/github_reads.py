"""Read-boundary protocol phase 1 tools depend on (FakeGitHub and real clients satisfy it)."""

from typing import Protocol

from issue_triage_agent.artifact import AuthorHistorySummary
from issue_triage_agent.fakes.github import IssueSnapshot


class GitHubReads(Protocol):
    """Read-only GitHub operations available to the phase 1 agent."""

    def fetch_issue(self, number: int) -> IssueSnapshot: ...

    def fetch_author_history(self, login: str) -> AuthorHistorySummary: ...
