"""Seam B: proposal artifact + issue number → GitHub write calls (phase 2)."""

import pytest

from issue_triage_agent.artifact import IssueKind, ProposalArtifact, TriageRole
from issue_triage_agent.fakes.github import FakeGitHub, WriteOp
from issue_triage_agent.phase2 import run_phase2
from tests.conftest import bug_artifact


def test_happy_path_creates_missing_labels_applies_and_posts_draft() -> None:
    github = FakeGitHub()

    run_phase2(bug_artifact(), 42, github=github)

    creates = [w for w in github.writes if w.op is WriteOp.CREATE_LABEL]
    assert {w.name for w in creates} == {"needs-triage"}
    apply = next(w for w in github.writes if w.op is WriteOp.APPLY_LABELS)
    assert apply.issue_number == 42
    assert apply.labels == ("bug", "needs-triage")
    comments = [w for w in github.writes if w.op is WriteOp.POST_COMMENT]
    assert len(comments) == 1
    assert comments[0].body == "Confirmed as a bug; thanks for the report."
    assert comments[0].issue_number == 42


def test_present_labels_are_not_recreated() -> None:
    github = FakeGitHub()
    github.seed_label("needs-triage")

    run_phase2(bug_artifact(), 42, github=github)

    creates = [w for w in github.writes if w.op is WriteOp.CREATE_LABEL]
    assert creates == []


def test_feature_label_created_and_enhancement_untouched() -> None:
    github = FakeGitHub()
    artifact = bug_artifact(
        issue_kind=IssueKind.FEATURE,
        labels=["feature", "needs-triage"],
        draft="Thanks for the feature idea; we'll consider it.",
    )

    run_phase2(artifact, 7, github=github)

    creates = [w.name for w in github.writes if w.op is WriteOp.CREATE_LABEL]
    assert "feature" in creates
    assert "enhancement" not in creates
    assert "enhancement" in github.labels
    for write in github.writes:
        if write.op is WriteOp.CREATE_LABEL:
            assert write.name != "enhancement"
        if write.op is WriteOp.APPLY_LABELS:
            assert "enhancement" not in (write.labels or ())


def test_fixed_role_mapping_needs_repro_gets_needs_info() -> None:
    github = FakeGitHub()
    artifact = bug_artifact(
        issue_kind=IssueKind.NEEDS_REPRO,
        triage_role=TriageRole.NEEDS_INFO,
        labels=["needs-repro", "needs-info"],
        draft="Please add repro steps and environment details.",
    )

    run_phase2(artifact, 9, github=github)

    creates = {w.name for w in github.writes if w.op is WriteOp.CREATE_LABEL}
    assert "needs-repro" in creates
    assert "needs-info" in creates
    apply = next(w for w in github.writes if w.op is WriteOp.APPLY_LABELS)
    assert apply.labels == ("needs-repro", "needs-info")


def test_fixed_role_mapping_other_kinds_get_needs_triage() -> None:
    github = FakeGitHub()

    run_phase2(bug_artifact(), 42, github=github)

    apply = next(w for w in github.writes if w.op is WriteOp.APPLY_LABELS)
    assert "needs-triage" in (apply.labels or ())


def test_empty_draft_means_no_writes_and_loud_failure() -> None:
    github = FakeGitHub()
    artifact = bug_artifact(draft="   ")

    with pytest.raises(ValueError, match="incomplete artifact"):
        run_phase2(artifact, 42, github=github)

    assert github.writes == []


def test_empty_labels_means_no_writes_and_loud_failure() -> None:
    github = FakeGitHub()
    artifact = bug_artifact(labels=[])

    with pytest.raises(ValueError, match="incomplete artifact"):
        run_phase2(artifact, 42, github=github)

    assert github.writes == []


def test_readiness_triage_role_rejected_with_no_writes() -> None:
    github = FakeGitHub()
    artifact = bug_artifact(
        triage_role=TriageRole.READY_FOR_AGENT,
        labels=["bug", "ready-for-agent"],
    )

    with pytest.raises(ValueError, match="readiness"):
        run_phase2(artifact, 42, github=github)

    assert github.writes == []


def test_role_mismatch_rejected_with_no_writes() -> None:
    github = FakeGitHub()
    artifact = bug_artifact(
        issue_kind=IssueKind.BUG,
        triage_role=TriageRole.NEEDS_INFO,
        labels=["bug", "needs-info"],
    )

    with pytest.raises(ValueError, match="fixed mapping"):
        run_phase2(artifact, 42, github=github)

    assert github.writes == []


def test_missing_role_label_rejected_before_any_write() -> None:
    github = FakeGitHub()
    artifact = bug_artifact(labels=["bug"])

    with pytest.raises(ValueError, match="role label"):
        run_phase2(artifact, 42, github=github)

    assert github.writes == []
