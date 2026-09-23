"""Seam A: feature/question kinds with Author History tailored Drafts."""

import json
from pathlib import Path

from langchain_core.messages import AIMessage

from issue_triage_agent.artifact import (
    AuthorHistorySummary,
    IssueKind,
    TriageRole,
)
from issue_triage_agent.fakes.github import FakeGitHub
from issue_triage_agent.fakes.llm import ScriptedLLM
from issue_triage_agent.payload import IssuePayload
from issue_triage_agent.phase1 import run_phase1


def _payload(
    title: str, body: str, login: str = "reporter", number: int = 42
) -> IssuePayload:
    return IssuePayload(
        number=number, title=title, body=body, author_login=login, comments=[]
    )


def _seeded_github(
    payload: IssuePayload, history: AuthorHistorySummary
) -> FakeGitHub:
    github = FakeGitHub()
    github.seed_issue(
        number=payload.number,
        title=payload.title,
        body=payload.body,
        author_login=payload.author_login,
        comments=list(payload.comments),
    )
    github.seed_author(payload.author_login, history)
    return github


def _newcomer() -> AuthorHistorySummary:
    return AuthorHistorySummary(first_time_contributor=True, prior_issue_count=0)


def _repeat() -> AuthorHistorySummary:
    return AuthorHistorySummary(first_time_contributor=False, prior_issue_count=12)


def _kind_llm(
    payload: IssuePayload,
    *,
    kind: str,
    draft: str,
    labels: list[str],
    history: AuthorHistorySummary | None = None,
) -> ScriptedLLM:
    return ScriptedLLM(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "fetch_issue",
                        "args": {"issue_number": payload.number},
                        "id": "call-fetch",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "fetch_author_history",
                        "args": {"login": payload.author_login},
                        "id": "call-author",
                    }
                ],
            ),
            AIMessage(content=_final_json(kind, draft, labels, history)),
        ]
    )


def _final_json(
    kind: str,
    draft: str,
    labels: list[str],
    history: AuthorHistorySummary | None = None,
) -> str:
    seen = history or AuthorHistorySummary(
        first_time_contributor=True, prior_issue_count=0
    )
    return json.dumps(
        {
            "issue_kind": kind,
            "triage_role": "needs-triage",
            "duplicate": {
                "is_duplicate": False,
                "canonical_issue_number": None,
            },
            "draft": draft,
            "labels": labels,
            "author_history": {
                "first_time_contributor": seen.first_time_contributor,
                "prior_issue_count": seen.prior_issue_count,
            },
        }
    )


def test_feature_issue_yields_feature_acknowledgement() -> None:
    payload = _payload(
        "Add dark mode",
        "It would be great to have a dark mode theme for night-time use.",
    )
    draft = "Thanks for the feature idea; dark mode is now on the list for consideration."

    artifact = run_phase1(
        payload,
        llm=_kind_llm(
            payload, kind="feature", draft=draft, labels=["feature", "needs-triage"]
        ),
        github=_seeded_github(payload, _newcomer()),
    )

    assert artifact.issue_kind is IssueKind.FEATURE
    assert artifact.triage_role is TriageRole.NEEDS_TRIAGE
    assert set(artifact.labels) == {"feature", "needs-triage"}
    assert artifact.draft.strip()


def test_question_issue_yields_question_acknowledgement() -> None:
    payload = _payload(
        "How do I configure the triage environment?",
        "I read the README but could not find how approval works.",
    )
    draft = "Good question; approval happens in the triage environment in Actions."

    artifact = run_phase1(
        payload,
        llm=_kind_llm(
            payload, kind="question", draft=draft, labels=["question", "needs-triage"]
        ),
        github=_seeded_github(payload, _newcomer()),
    )

    assert artifact.issue_kind is IssueKind.QUESTION
    assert artifact.triage_role is TriageRole.NEEDS_TRIAGE
    assert set(artifact.labels) == {"question", "needs-triage"}
    assert artifact.draft.strip()


def test_newcomer_draft_welcomes_first_time_reporter() -> None:
    payload = _payload(
        "Add dark mode",
        "It would be great to have a dark mode theme.",
        login="newbie",
    )
    draft = "Welcome, and thanks for your first report; dark mode is noted."

    artifact = run_phase1(
        payload,
        llm=_kind_llm(
            payload, kind="feature", draft=draft, labels=["feature", "needs-triage"]
        ),
        github=_seeded_github(payload, _newcomer()),
    )

    assert artifact.author_history.first_time_contributor is True
    assert "welcome" in artifact.draft.lower()
    assert "first" in artifact.draft.lower()


def test_repeat_reporter_draft_acknowledges_history() -> None:
    payload = _payload(
        "Add dark mode",
        "It would be great to have a dark mode theme.",
        login="regular",
    )
    draft = "Thanks for another report (12 prior issues); dark mode is noted."

    artifact = run_phase1(
        payload,
        llm=_kind_llm(
            payload,
            kind="feature",
            draft=draft,
            labels=["feature", "needs-triage"],
            history=_repeat(),
        ),
        github=_seeded_github(payload, _repeat()),
    )

    assert artifact.author_history.first_time_contributor is False
    assert artifact.author_history.prior_issue_count == 12
    assert "12" in artifact.draft


def test_docs_results_reach_the_draft(tmp_path: Path) -> None:
    root = tmp_path
    (root / "README.md").write_text("# Repo\nDark mode lives on the roadmap.\n")
    docs = root / "docs"
    docs.mkdir()
    (docs / "testing.md").write_text("Write a failing test first.\n")

    payload = _payload(
        "How do I write repro steps?",
        "I want to file a good bug report; where are repro steps described?",
    )
    llm = ScriptedLLM(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_docs",
                        "args": {"query": "failing test"},
                        "id": "call-docs",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "fetch_issue",
                        "args": {"issue_number": payload.number},
                        "id": "call-fetch",
                    }
                ],
            ),
            AIMessage(content=_final_json(
                "question",
                "See docs/testing.md: write a failing test first.",
                ["question", "needs-triage"],
            )),
        ]
    )

    artifact = run_phase1(
        payload, llm=llm, github=_seeded_github(payload, _newcomer()), docs_root=root
    )

    assert artifact.issue_kind is IssueKind.QUESTION
    assert "docs/testing.md" in artifact.draft
    assert "failing test" in artifact.draft
