"""Phase entry points: event payload -> artifact file -> write calls.

Phase 1 main runs the agent (injected LLM + reads) and writes the proposal
artifact file; phase 2 main loads the approved artifact file and performs
the writes (injected writer) with no LLM anywhere in its path. Failures
exit nonzero before any write touches the issue.
"""

import inspect
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

from issue_triage_agent.artifact import ProposalArtifact
from issue_triage_agent.fakes.github import FakeGitHub, WriteOp
from issue_triage_agent.fakes.llm import ScriptedLLM
from issue_triage_agent.payload import IssuePayload
from issue_triage_agent.phase1_main import main as phase1_main
from issue_triage_agent.phase2_main import main as phase2_main
from issue_triage_agent.workflow import (
    ARTIFACT_FILENAME,
    payload_from_event,
    read_artifact_file,
    write_artifact_file,
)
from tests.conftest import (
    bug_artifact,
    complete_bug_payload,
    seeded_github_for_bug,
)


def _event_for_bug() -> dict[str, Any]:
    payload = complete_bug_payload()
    return {
        "issue": {
            "number": payload["number"],
            "title": payload["title"],
            "body": payload["body"],
            "user": {"login": payload["author_login"]},
        }
    }


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


def _write_event(tmp_path: Path, event: dict[str, Any]) -> Path:
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event), encoding="utf-8")
    return path


def test_payload_from_event_reads_issue_fields() -> None:
    payload = payload_from_event(_event_for_bug())

    assert isinstance(payload, IssuePayload)
    assert payload.number == 42
    assert payload.title == "App crashes on save"
    assert "ValueError" in payload.body
    assert payload.author_login == "reporter"
    assert payload.comments == []


def test_phase1_main_writes_well_formed_artifact_file(tmp_path: Path) -> None:
    event_path = _write_event(tmp_path, _event_for_bug())
    out = tmp_path / ARTIFACT_FILENAME

    exit_code = phase1_main(
        ["--event-path", str(event_path), "--out", str(out)],
        make_llm=_happy_path_bug_llm,
        make_reads=seeded_github_for_bug,
    )

    assert exit_code == 0
    artifact = ProposalArtifact.model_validate_json(out.read_text(encoding="utf-8"))
    assert artifact.draft.strip()
    assert set(artifact.labels) == {"bug", "needs-triage"}


def test_phase1_main_failure_exits_nonzero_with_no_artifact_file(
    tmp_path: Path,
) -> None:
    from issue_triage_agent.fakes.llm import ScriptedLLM as LLM

    event_path = _write_event(tmp_path, _event_for_bug())
    out = tmp_path / ARTIFACT_FILENAME

    exit_code = phase1_main(
        ["--event-path", str(event_path), "--out", str(out)],
        make_llm=lambda: LLM(messages=[]),
        make_reads=seeded_github_for_bug,
    )

    assert exit_code == 1
    assert not out.exists()


def test_phase2_main_applies_exactly_the_approved_artifact(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / ARTIFACT_FILENAME
    write_artifact_file(artifact_path, bug_artifact())
    github = FakeGitHub()

    exit_code = phase2_main(
        ["--artifact", str(artifact_path), "--issue-number", "42"],
        make_writes=lambda: github,
    )

    assert exit_code == 0
    apply = next(w for w in github.writes if w.op is WriteOp.APPLY_LABELS)
    assert apply.issue_number == 42
    assert apply.labels == ("bug", "needs-triage")
    comments = [w for w in github.writes if w.op is WriteOp.POST_COMMENT]
    assert len(comments) == 1
    assert comments[0].body == "Confirmed as a bug; thanks for the report."


def test_phase2_main_takes_no_llm() -> None:
    params = inspect.signature(phase2_main).parameters
    assert "llm" not in params
    assert "model" not in params
    assert "make_llm" not in params


def test_phase2_main_malformed_artifact_exits_nonzero_with_no_writes(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / ARTIFACT_FILENAME
    artifact_path.write_text('{"issue_kind": "bug", broken', encoding="utf-8")
    github = FakeGitHub()

    exit_code = phase2_main(
        ["--artifact", str(artifact_path), "--issue-number", "42"],
        make_writes=lambda: github,
    )

    assert exit_code == 1
    assert github.writes == []


def test_phase2_main_invalid_artifact_exits_nonzero_with_no_writes(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / ARTIFACT_FILENAME
    write_artifact_file(artifact_path, bug_artifact(labels=[]))
    github = FakeGitHub()

    exit_code = phase2_main(
        ["--artifact", str(artifact_path), "--issue-number", "42"],
        make_writes=lambda: github,
    )

    assert exit_code == 1
    assert github.writes == []


def test_artifact_file_round_trip(tmp_path: Path) -> None:
    path = tmp_path / ARTIFACT_FILENAME
    write_artifact_file(path, bug_artifact())

    assert read_artifact_file(path) == bug_artifact()
