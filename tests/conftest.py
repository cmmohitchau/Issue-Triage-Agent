"""Fixture builders for the two-seam suite: payload in, artifact/write assertions out."""

from issue_triage_agent.artifact import (
    AuthorHistorySummary,
    IssueKind,
    ProposalArtifact,
    TriageRole,
)
from issue_triage_agent.fakes.github import FakeGitHub
from issue_triage_agent.fakes.llm import ScriptedLLM


def complete_bug_payload() -> dict[str, object]:
    """A well-formed issue payload that satisfies the complete-bug rubric (kind=bug)."""
    return {
        "number": 42,
        "title": "App crashes on save",
        "body": (
            "Steps to reproduce:\n1. Open file\n2. Click save\n\n"
            "Error:\nValueError: invalid path\n\n"
            "Version: 1.2.3\nOS: Windows 11"
        ),
        "comments": [],
        "author_login": "reporter",
    }


def complete_bug_artifact_dict(**overrides: object) -> dict[str, object]:
    """Known-good complete-bug artifact fields for seam B tests."""
    base: dict[str, object] = {
        "issue_kind": IssueKind.BUG,
        "triage_role": TriageRole.NEEDS_TRIAGE,
        "duplicate": {"is_duplicate": False, "canonical_issue_number": None},
        "draft": "Confirmed as a bug; thanks for the report.",
        "labels": ["bug", "needs-triage"],
        "author_history": {
            "first_time_contributor": True,
            "prior_issue_count": 0,
        },
    }
    base.update(overrides)
    return base


def bug_artifact(**overrides: object) -> ProposalArtifact:
    """A known-good complete-bug artifact for seam B tests."""
    return ProposalArtifact.model_validate(complete_bug_artifact_dict(**overrides))


def seeded_github_for_bug() -> FakeGitHub:
    payload = complete_bug_payload()
    github = FakeGitHub()
    github.seed_issue(
        number=int(payload["number"]),  # type: ignore[arg-type]
        title=str(payload["title"]),
        body=str(payload["body"]),
        author_login=str(payload["author_login"]),
        comments=list(payload["comments"]),  # type: ignore[arg-type]
    )
    github.seed_author(
        "reporter",
        AuthorHistorySummary(first_time_contributor=True, prior_issue_count=0),
    )
    return github


def empty_llm() -> ScriptedLLM:
    return ScriptedLLM(messages=[])
