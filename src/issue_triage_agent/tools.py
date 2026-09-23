"""Read-only agent tools bound to a GitHub read boundary (phase 1 has no write tools)."""

from pathlib import Path

from langchain_core.tools import BaseTool, tool

from issue_triage_agent.github_reads import GitHubReads

#: Docs-searchable suffixes under the docs tree.
_DOCS_SUFFIXES = frozenset({".md", ".mdx", ".txt", ".rst"})

#: Most matching lines kept per file before truncating a hit.
_MAX_LINES_PER_FILE = 3

#: Most files reported per query.
_MAX_FILES = 5


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


def default_docs_root() -> Path:
    """Working directory owning the README + docs tree (the workflow runs here)."""
    return Path.cwd()


def make_search_docs(root: Path | None = None) -> BaseTool:
    """search_docs: keyword search over README.md and the docs tree only.

    Source files, root siblings of the README, and non-docs trees are never
    searched, so Draft links point at documentation rather than code.
    """

    base = root if root is not None else default_docs_root()

    @tool
    def search_docs(query: str) -> str:
        """Keyword search over the README and docs tree; returns top hits."""
        tokens = [t for t in query.lower().split() if t]
        if not tokens:
            return _no_docs(query)
        hits = [
            f"{path.relative_to(base).as_posix()}:\n{snippet}"
            for path, snippet in _search_files(base, tokens)
        ]
        if not hits:
            return _no_docs(query)
        return "\n".join(hits)

    return search_docs


def _no_docs(query: str) -> str:
    """Miss message shared by empty and hitless queries."""
    return f"No docs found for {query!r}."


def _search_files(base: Path, tokens: list[str]) -> list[tuple[Path, str]]:
    """Matching (file, snippet) pairs, README first, capped at _MAX_FILES."""
    candidates = [base / "README.md"]
    docs_dir = base / "docs"
    if docs_dir.is_dir():
        candidates.extend(sorted(docs_dir.rglob("*")))
    found: list[tuple[Path, str]] = []
    for path in candidates:
        if len(found) >= _MAX_FILES:
            break
        if not _is_searchable(base, path):
            continue
        snippet = _matching_lines(path, tokens)
        if snippet:
            found.append((path, snippet))
    return found


def _is_searchable(base: Path, path: Path) -> bool:
    """Only the root README and docs-tree text files are searchable."""
    if not path.is_file() or path.is_symlink():
        return False
    if path == base / "README.md":
        return True
    try:
        path.relative_to(base / "docs")
    except ValueError:
        return False
    return path.suffix.lower() in _DOCS_SUFFIXES


def _matching_lines(path: Path, tokens: list[str]) -> str:
    """Up to _MAX_LINES_PER_FILE stripped lines containing any token."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and any(token in line.lower() for token in tokens)
    ]
    return "\n".join(lines[:_MAX_LINES_PER_FILE])
