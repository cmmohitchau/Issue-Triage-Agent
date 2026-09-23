"""Fake GitHub boundary: scripted reads plus a write recorder for seam B."""

import pytest

from issue_triage_agent.artifact import AuthorHistorySummary
from issue_triage_agent.fakes.github import FakeGitHub, WriteCall, WriteOp
from tests.conftest import bug_artifact, seeded_github_for_bug


def test_fetch_issue_returns_title_body_comments_and_author() -> None:
    github = seeded_github_for_bug()

    issue = github.fetch_issue(42)

    assert issue.number == 42
    assert issue.title == "App crashes on save"
    assert "ValueError" in issue.body
    assert issue.author_login == "reporter"
    assert issue.comments == ()


def test_fetch_author_history_signals() -> None:
    github = FakeGitHub()
    github.seed_author(
        "newbie",
        AuthorHistorySummary(first_time_contributor=True, prior_issue_count=0),
    )
    github.seed_author(
        "regular",
        AuthorHistorySummary(first_time_contributor=False, prior_issue_count=12),
    )

    newbie = github.fetch_author_history("newbie")
    regular = github.fetch_author_history("regular")

    assert newbie.first_time_contributor is True
    assert newbie.prior_issue_count == 0
    assert regular.first_time_contributor is False
    assert regular.prior_issue_count == 12


def test_fetch_unknown_author_raises() -> None:
    github = FakeGitHub()

    with pytest.raises(KeyError):
        github.fetch_author_history("ghost")


def test_duplicate_search_returns_existing_issue_hits() -> None:
    github = FakeGitHub()
    github.seed_search_hit(
        number=3,
        title="Crash when saving",
        snippet="ValueError on save",
    )

    hits = github.search_issues("crash save")

    assert len(hits) == 1
    assert hits[0].number == 3
    assert hits[0].title == "Crash when saving"


def test_duplicate_search_miss_returns_empty() -> None:
    github = FakeGitHub()

    assert github.search_issues("anything") == []


def test_seam_b_artifact_drives_recorded_writes() -> None:
    github = seeded_github_for_bug()
    artifact = bug_artifact()

    github.apply_labels(42, list(artifact.labels))
    github.post_comment(42, artifact.draft)

    assert github.writes == [
        WriteCall(
            op=WriteOp.APPLY_LABELS,
            issue_number=42,
            labels=("bug", "needs-triage"),
        ),
        WriteCall(
            op=WriteOp.POST_COMMENT,
            issue_number=42,
            body="Confirmed as a bug; thanks for the report.",
        ),
    ]


def test_write_calls_are_recorded_not_sent() -> None:
    github = FakeGitHub()

    github.create_label_if_missing("feature")
    github.apply_labels(7, ["bug", "needs-triage"])
    github.post_comment(7, "Confirmed as a bug.")

    assert github.writes == [
        WriteCall(op=WriteOp.CREATE_LABEL, name="feature"),
        WriteCall(
            op=WriteOp.APPLY_LABELS,
            issue_number=7,
            labels=("bug", "needs-triage"),
        ),
        WriteCall(op=WriteOp.POST_COMMENT, issue_number=7, body="Confirmed as a bug."),
    ]


def test_fetch_unknown_issue_raises() -> None:
    github = FakeGitHub()

    with pytest.raises(KeyError):
        github.fetch_issue(999)
