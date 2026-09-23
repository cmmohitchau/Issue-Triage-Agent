"""Seam A: under-specified bug reports -> needs-repro proposal artifacts."""

import json

from langchain_core.messages import AIMessage

from issue_triage_agent.artifact import (
    AuthorHistorySummary,
    IssueKind,
    TriageRole,
)
from issue_triage_agent.fakes.github import FakeGitHub
from issue_triage_agent.fakes.llm import ScriptedLLM
from issue_triage_agent.payload import IssuePayload
from issue_triage_agent.phase1 import NEEDS_REPRO_RUBRIC, SYSTEM_PROMPT, run_phase1
from tests.conftest import complete_bug_payload, seeded_github_for_bug


def _payload(body: str) -> IssuePayload:
    return IssuePayload(
        number=42,
        title="App crashes on save",
        body=body,
        author_login="reporter",
        comments=[],
    )


def _missing_repro_body() -> str:
    return "Saving is broken for me.\n\nVersion: 1.2.3\nOS: Windows 11"


def _missing_env_body() -> str:
    return (
        "Steps to reproduce:\n1. Open file\n2. Click save\n\n"
        "Error:\nValueError: invalid path"
    )


def _missing_both_body() -> str:
    return "Saving is broken for me, please help."


def _seeded_github(payload: IssuePayload) -> FakeGitHub:
    github = FakeGitHub()
    github.seed_issue(
        number=payload.number,
        title=payload.title,
        body=payload.body,
        author_login=payload.author_login,
        comments=list(payload.comments),
    )
    github.seed_author(
        payload.author_login,
        AuthorHistorySummary(first_time_contributor=True, prior_issue_count=0),
    )
    return github


def _needs_repro_llm(draft: str) -> ScriptedLLM:
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
                    '{"issue_kind": "needs-repro",'
                    ' "triage_role": "needs-info",'
                    ' "duplicate": {"is_duplicate": false,'
                    ' "canonical_issue_number": null},'
                    f' "draft": {json.dumps(draft)},'
                    ' "labels": ["needs-repro", "needs-info"],'
                    ' "author_history": {"first_time_contributor": true,'
                    ' "prior_issue_count": 0}}'
                )
            ),
        ]
    )


def test_missing_repro_yields_needs_repro() -> None:
    payload = _payload(_missing_repro_body())
    draft = (
        "Thanks for the report. Before this can be worked, "
        "please add reproduction steps or the exact error text."
    )

    artifact = run_phase1(
        payload, llm=_needs_repro_llm(draft), github=_seeded_github(payload)
    )

    assert artifact.issue_kind is IssueKind.NEEDS_REPRO
    assert artifact.triage_role is TriageRole.NEEDS_INFO
    assert set(artifact.labels) == {"needs-repro", "needs-info"}
    assert "repro" in artifact.draft.lower()


def test_missing_env_yields_needs_repro() -> None:
    payload = _payload(_missing_env_body())
    draft = (
        "Thanks for the report. Before this can be worked, "
        "please add your app version and OS/runtime."
    )

    artifact = run_phase1(
        payload, llm=_needs_repro_llm(draft), github=_seeded_github(payload)
    )

    assert artifact.issue_kind is IssueKind.NEEDS_REPRO
    assert artifact.triage_role is TriageRole.NEEDS_INFO
    assert set(artifact.labels) == {"needs-repro", "needs-info"}
    assert "version" in artifact.draft.lower()
    assert "os" in artifact.draft.lower()


def test_missing_both_names_both_gaps() -> None:
    payload = _payload(_missing_both_body())
    draft = (
        "Thanks for the report. Before this can be worked, please add "
        "reproduction steps (or the exact error text) plus your app "
        "version and OS/runtime."
    )

    artifact = run_phase1(
        payload, llm=_needs_repro_llm(draft), github=_seeded_github(payload)
    )

    assert artifact.issue_kind is IssueKind.NEEDS_REPRO
    assert artifact.triage_role is TriageRole.NEEDS_INFO
    assert set(artifact.labels) == {"needs-repro", "needs-info"}
    lowered = artifact.draft.lower()
    assert "repro" in lowered
    assert "version" in lowered
    assert "os" in lowered


def test_needs_repro_rubric_appears_verbatim_in_prompt() -> None:
    assert NEEDS_REPRO_RUBRIC in SYSTEM_PROMPT
    assert "reproduction steps" in NEEDS_REPRO_RUBRIC
    assert "verbatim error" in NEEDS_REPRO_RUBRIC
    assert "version" in NEEDS_REPRO_RUBRIC
    assert "OS/runtime" in NEEDS_REPRO_RUBRIC
    assert "needs-repro" in NEEDS_REPRO_RUBRIC


def test_complete_bug_still_classifies_bug() -> None:
    payload = IssuePayload.model_validate(complete_bug_payload())
    llm = ScriptedLLM(
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

    artifact = run_phase1(payload, llm=llm, github=seeded_github_for_bug())

    assert artifact.issue_kind is IssueKind.BUG
    assert artifact.triage_role is TriageRole.NEEDS_TRIAGE
