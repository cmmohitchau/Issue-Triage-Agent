"""Seam A/B boundary: the proposal artifact both phases share."""

from enum import Enum

from pydantic import BaseModel, Field


class IssueKind(str, Enum):
    """Durable nature of an issue, assigned once at triage."""

    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"
    DUPLICATE = "duplicate"
    NEEDS_REPRO = "needs-repro"


class TriageRole(str, Enum):
    """Where an issue sits in the maintainer's workflow queue."""

    NEEDS_TRIAGE = "needs-triage"
    NEEDS_INFO = "needs-info"
    READY_FOR_AGENT = "ready-for-agent"
    READY_FOR_HUMAN = "ready-for-human"
    WONTFIX = "wontfix"


class AuthorHistorySummary(BaseModel):
    """Cheap author-history signals used to tailor the Draft."""

    first_time_contributor: bool
    prior_issue_count: int = Field(ge=0)


class DuplicateVerdict(BaseModel):
    """Binary duplicate judgement; canonical original when confirmed."""

    is_duplicate: bool
    canonical_issue_number: int | None = None


class ProposalArtifact(BaseModel):
    """The only output of phase 1 and the only input of phase 2."""

    issue_kind: IssueKind
    triage_role: TriageRole
    duplicate: DuplicateVerdict
    draft: str
    labels: list[str]
    author_history: AuthorHistorySummary
