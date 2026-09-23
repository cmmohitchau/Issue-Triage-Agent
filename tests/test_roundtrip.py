"""Artifact contract round-trip: phase 1 output drives phase 2 writes unchanged.

Seam boundary: ProposalArtifact is the only output of phase 1 and the only
input of phase 2. A well-formed artifact passes through JSON (the Actions
artifact handoff shape) with no transformation; a contract-violating
artifact fails loud before the first write, never partially applying.
"""

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from issue_triage_agent.artifact import IssueKind, ProposalArtifact, TriageRole
from issue_triage_agent.fakes.github import FakeGitHub, WriteOp
from issue_triage_agent.fakes.llm import ScriptedLLM
from issue_triage_agent.payload import IssuePayload
from issue_triage_agent.phase1 import run_phase1
from issue_triage_agent.phase2 import run_phase2
from tests.conftest import (
    bug_artifact,
    complete_bug_artifact_dict,
    complete_bug_payload,
    seeded_github_for_bug,
)


def _payload() -> IssuePayload:
    return IssuePayload.model_validate(complete_bug_payload())


def _happy_path_bug_llm() -> ScriptedLLM:
    return ScriptedLLM(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "fetch_issue",
                        "args": {"issue_number": 42},
                        "id": "call-fetch",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "fetch_author_history",
                        "args": {"login": "reporter"},
                        "id": "call-author",
                    }
                ],
            ),
            AIMessage(
                content=(
                    '{"issue_kind": "bug",'
                    ' "triage_role": "needs-triage",'
                    ' "duplicate": {"is_duplicate": false,'
                    ' "canonical_issue_number": null},'
                    ' "draft": "Confirmed as a bug; thanks for the report.",'
                    ' "labels": ["bug", "needs-triage"],'
                    ' "author_history": {"first_time_contributor": true,'
                    ' "prior_issue_count": 0}}'
                )
            ),
        ]
    )


def _phase1_artifact() -> ProposalArtifact:
    return run_phase1(_payload(), llm=_happy_path_bug_llm(), github=seeded_github_for_bug())


def test_phase1_artifact_feeds_phase2_with_no_transformation() -> None:
    artifact = _phase1_artifact()
    before = artifact.model_dump()
    # Fresh boundary: phase 2 sees only the artifact + issue number, no shared memory.
    github = FakeGitHub()

    run_phase2(artifact, 42, github=github)

    assert artifact.model_dump() == before

    apply = next(w for w in github.writes if w.op is WriteOp.APPLY_LABELS)
    assert apply.issue_number == 42
    assert apply.labels == tuple(artifact.labels)
    comments = [w for w in github.writes if w.op is WriteOp.POST_COMMENT]
    assert len(comments) == 1
    assert comments[0].issue_number == 42
    assert comments[0].body == artifact.draft


def test_round_trip_via_json_preserves_artifact_and_writes() -> None:
    artifact = _phase1_artifact()

    restored = ProposalArtifact.model_validate_json(artifact.model_dump_json())

    assert restored == artifact
    github = FakeGitHub()
    run_phase2(restored, 42, github=github)

    apply = next(w for w in github.writes if w.op is WriteOp.APPLY_LABELS)
    assert apply.labels == ("bug", "needs-triage")
    comments = [w for w in github.writes if w.op is WriteOp.POST_COMMENT]
    assert len(comments) == 1
    assert comments[0].body == "Confirmed as a bug; thanks for the report."


def test_round_trip_via_artifact_file(tmp_path: Path) -> None:
    path = tmp_path / "proposal.json"
    artifact = _phase1_artifact()
    path.write_text(artifact.model_dump_json(), encoding="utf-8")

    restored = ProposalArtifact.model_validate_json(
        path.read_text(encoding="utf-8")
    )

    assert restored == artifact
    github = FakeGitHub()
    run_phase2(restored, 42, github=github)
    assert [w.op for w in github.writes] == [
        WriteOp.CREATE_LABEL,
        WriteOp.APPLY_LABELS,
        WriteOp.POST_COMMENT,
    ]


def test_malformed_json_fails_loud() -> None:
    with pytest.raises(ValidationError):
        ProposalArtifact.model_validate_json('{"issue_kind": "bug", broken')


def test_incomplete_artifact_dicts_fail_loud() -> None:
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


def test_closed_vocabulary_violation_fails_loud() -> None:
    with pytest.raises(ValidationError):
        ProposalArtifact.model_validate(
            complete_bug_artifact_dict(issue_kind="enhancement")
        )


def test_empty_draft_and_empty_labels_fail_loud_with_no_partial_writes() -> None:
    for artifact in (bug_artifact(draft="   "), bug_artifact(labels=[])):
        github = FakeGitHub()

        with pytest.raises(ValueError, match="incomplete artifact"):
            run_phase2(artifact, 42, github=github)

        assert github.writes == []


def test_role_violations_fail_loud_with_no_partial_writes() -> None:
    cases = [
        bug_artifact(
            triage_role=TriageRole.READY_FOR_AGENT,
            labels=["bug", "ready-for-agent"],
        ),
        bug_artifact(
            issue_kind=IssueKind.BUG,
            triage_role=TriageRole.NEEDS_INFO,
            labels=["bug", "needs-info"],
        ),
        bug_artifact(labels=["bug"]),
    ]
    for artifact in cases:
        github = FakeGitHub()

        with pytest.raises(ValueError):
            run_phase2(artifact, 42, github=github)

        assert github.writes == []


def test_write_calls_match_artifact_fields_exactly() -> None:
    artifact = _phase1_artifact()
    assert json.loads(artifact.model_dump_json())["labels"] == ["bug", "needs-triage"]

    github = FakeGitHub()
    run_phase2(artifact, 42, github=github)

    creates = {w.name for w in github.writes if w.op is WriteOp.CREATE_LABEL}
    assert creates == {"needs-triage"}
    apply = next(w for w in github.writes if w.op is WriteOp.APPLY_LABELS)
    assert list(apply.labels or ()) == list(artifact.labels)
