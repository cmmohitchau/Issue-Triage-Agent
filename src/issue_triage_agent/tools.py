"""Read-only agent tools bound to a GitHub read boundary (phase 1 has no write tools)."""

from langchain_core.tools import BaseTool, tool

from issue_triage_agent.github_reads import GitHubReads


def make_fetch_issue(github: GitHubReads) -> BaseTool:
    """fetch_issue: read title/body/comments/author for one issue."""

    @tool
    def fetch_issue(issue_number: int) -> str:
        """Fetch one issue's title, body, comments, and author login."""
        issue = github.fetch_issue(issue_number)
        comments = "\n".join(issue.comments) if issue.comments else "(no comments)"
        return (
            f"#{issue.number}: {issue.title}\n"
            f"Author: {issue.author_login}\n"
            f"Body:\n{issue.body}\n"
            f"Comments:\n{comments}"
        )

    return fetch_issue


def make_fetch_author_history(github: GitHubReads) -> BaseTool:
    """fetch_author_history: first-time flag + prior issue count for a login."""

    @tool
    def fetch_author_history(login: str) -> str:
        """Fetch Author History: first-time-contributor flag and prior issue count."""
        history = github.fetch_author_history(login)
        return (
            f"first_time_contributor={history.first_time_contributor}; "
            f"prior_issue_count={history.prior_issue_count}"
        )

    return fetch_author_history
