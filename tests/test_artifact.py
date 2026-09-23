"""Proposal artifact is typed, JSON-round-trippable, and validates invariants."""

import json

import pytest
from pydantic import ValidationError

from issue_triage_agent.artifact import (
    AuthorHistorySummary,
    DuplicateVerdict,
    IssueKind,
    ProposalArtifact,
    TriageRole,
)
from tests.conftest import complete_bug_artifact_dict


def test_artifact_round_trips_through_json() -> None:
    original = ProposalArtifact.model_validate(complete_bug_artifact_dict())

    restored = ProposalArtifact.model_validate_json(original.model_dump_json())

    assert restored == original
    assert restored.issue_kind is IssueKind.BUG
    assert restored.triage_role is TriageRole.NEEDS_TRIAGE
    assert json.loads(original.model_dump_json())["labels"] == [
        "bug",
        "needs-triage",
    ]


def test_artifact_requires_every_seam_field() -> None:
    for field in (
        "issue_kind",
        "triage_role",
        "duplicate",
        "draft",
        "labels",
        "author_history",
    ):
        incomplete = complete_bug_artifact_dict()
        del incomplete[field]
        with pytest.raises(ValidationError):
            ProposalArtifact.model_validate(incomplete)


def test_issue_kind_is_closed_vocabulary() -> None:
    with pytest.raises(ValidationError):
        ProposalArtifact.model_validate(
            complete_bug_artifact_dict(issue_kind="enhancement")
        )


def test_confirmed_duplicate_carries_canonical_issue_number() -> None:
    artifact = ProposalArtifact.model_validate(
        complete_bug_artifact_dict(
            issue_kind=IssueKind.DUPLICATE,
            triage_role=TriageRole.NEEDS_TRIAGE,
            duplicate={"is_duplicate": True, "canonical_issue_number": 42},
            labels=["duplicate", "needs-triage"],
            draft="Looks like a duplicate of #42.",
        )
    )

    assert artifact.duplicate.is_duplicate is True
    assert artifact.duplicate.canonical_issue_number == 42


def test_author_history_rejects_negative_prior_issue_count() -> None:
    with pytest.raises(ValidationError):
        AuthorHistorySummary(first_time_contributor=False, prior_issue_count=-1)


def test_duplicate_verdict_defaults_canonical_to_none() -> None:
    verdict = DuplicateVerdict.model_validate({"is_duplicate": False})

    assert verdict.canonical_issue_number is None
