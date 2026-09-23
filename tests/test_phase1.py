"""Seam A: issue payload → proposal artifact (phase 1 happy path)."""

from langchain_core.messages import AIMessage

from issue_triage_agent.artifact import IssueKind, ProposalArtifact, TriageRole
from issue_triage_agent.fakes.github import ReadOp
from issue_triage_agent.fakes.llm import ScriptedLLM
from issue_triage_agent.payload import IssuePayload
from issue_triage_agent.phase1 import run_phase1
from tests.conftest import complete_bug_payload, seeded_github_for_bug


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


def test_complete_bug_payload_yields_well_formed_artifact() -> None:
    github = seeded_github_for_bug()

    artifact = run_phase1(_payload(), llm=_happy_path_bug_llm(), github=github)

    assert isinstance(artifact, ProposalArtifact)
    assert artifact.issue_kind is IssueKind.BUG
    assert artifact.triage_role is TriageRole.NEEDS_TRIAGE
    assert artifact.draft.strip()
    assert set(artifact.labels) == {"bug", "needs-triage"}
    assert artifact.duplicate.is_duplicate is False
    assert artifact.author_history.first_time_contributor is True
    assert artifact.author_history.prior_issue_count == 0


def test_react_loop_calls_fetch_issue_tool() -> None:
    github = seeded_github_for_bug()

    run_phase1(_payload(), llm=_happy_path_bug_llm(), github=github)

    assert ReadOp.FETCH_ISSUE in github.reads
    assert ReadOp.FETCH_AUTHOR_HISTORY in github.reads


def test_issue_comments_reach_the_agent_via_fetch_issue() -> None:
    payload = _payload()
    payload.comments = ["Also fails on Linux with the same ValueError"]
    github = seeded_github_for_bug()

    run_phase1(payload, llm=_happy_path_bug_llm(), github=github)

    assert ReadOp.FETCH_ISSUE in github.reads
    issue = github.fetch_issue(payload.number)
    assert issue.comments == ("Also fails on Linux with the same ValueError",)
