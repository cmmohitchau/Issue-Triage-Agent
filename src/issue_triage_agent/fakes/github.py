"""Fake GitHub at the network boundary: scripted reads, recorded writes."""

from dataclasses import dataclass
from enum import Enum

from issue_triage_agent.artifact import AuthorHistorySummary
from issue_triage_agent.label_policy import EXISTING_LABELS

#: Labels already on the repo per spec (shared with phase 2 policy).
DEFAULT_LABELS = EXISTING_LABELS


class WriteOp(str, Enum):
    """Discriminator for recorded GitHub write calls (not Issue Kind)."""

    CREATE_LABEL = "create_label"
    APPLY_LABELS = "apply_labels"
    POST_COMMENT = "post_comment"


class ReadOp(str, Enum):
    """Discriminator for recorded GitHub read calls at the fake boundary."""

    FETCH_ISSUE = "fetch_issue"
    FETCH_AUTHOR_HISTORY = "fetch_author_history"
    SEARCH_ISSUES = "search_issues"


@dataclass(frozen=True)
class IssueSnapshot:
    number: int
    title: str
    body: str
    comments: tuple[str, ...]
    author_login: str


@dataclass(frozen=True)
class SearchHit:
    number: int
    title: str
    snippet: str


@dataclass(frozen=True)
class WriteCall:
    op: WriteOp
    name: str | None = None
    issue_number: int | None = None
    labels: tuple[str, ...] | None = None
    body: str | None = None


@dataclass
class _SeededIssue:
    number: int
    title: str
    body: str
    comments: list[str]
    author_login: str


class FakeGitHub:
    """In-memory GitHub: injectable reads for phase 1, write log for phase 2."""

    def __init__(self) -> None:
        self._issues: dict[int, _SeededIssue] = {}
        self._authors: dict[str, AuthorHistorySummary] = {}
        self._search_hits: list[SearchHit] = []
        self._labels: set[str] = set(DEFAULT_LABELS)
        self.reads: list[ReadOp] = []
        self.writes: list[WriteCall] = []

    @property
    def labels(self) -> frozenset[str]:
        return frozenset(self._labels)

    def seed_label(self, name: str) -> None:
        self._labels.add(name)

    def seed_issue(
        self,
        *,
        number: int,
        title: str,
        body: str,
        author_login: str,
        comments: list[str] | None = None,
    ) -> None:
        self._issues[number] = _SeededIssue(
            number=number,
            title=title,
            body=body,
            comments=list(comments or []),
            author_login=author_login,
        )

    def seed_author(self, login: str, history: AuthorHistorySummary) -> None:
        self._authors[login] = history

    def seed_search_hit(self, *, number: int, title: str, snippet: str) -> None:
        self._search_hits.append(
            SearchHit(number=number, title=title, snippet=snippet)
        )

    def fetch_issue(self, number: int) -> IssueSnapshot:
        self.reads.append(ReadOp.FETCH_ISSUE)
        issue = self._issues[number]
        return IssueSnapshot(
            number=issue.number,
            title=issue.title,
            body=issue.body,
            comments=tuple(issue.comments),
            author_login=issue.author_login,
        )

    def fetch_author_history(self, login: str) -> AuthorHistorySummary:
        self.reads.append(ReadOp.FETCH_AUTHOR_HISTORY)
        return self._authors[login]

    def search_issues(self, query: str) -> list[SearchHit]:
        self.reads.append(ReadOp.SEARCH_ISSUES)
        tokens = [t for t in query.lower().split() if t]
        if not tokens:
            return []
        return [
            hit
            for hit in self._search_hits
            if any(
                token in hit.title.lower() or token in hit.snippet.lower()
                for token in tokens
            )
        ]

    def create_label_if_missing(self, name: str) -> None:
        if name not in self._labels:
            self._labels.add(name)
            self.writes.append(WriteCall(op=WriteOp.CREATE_LABEL, name=name))

    def apply_labels(self, issue_number: int, labels: list[str]) -> None:
        self.writes.append(
            WriteCall(
                op=WriteOp.APPLY_LABELS,
                issue_number=issue_number,
                labels=tuple(labels),
            )
        )

    def post_comment(self, issue_number: int, body: str) -> None:
        self.writes.append(
            WriteCall(op=WriteOp.POST_COMMENT, issue_number=issue_number, body=body)
        )
