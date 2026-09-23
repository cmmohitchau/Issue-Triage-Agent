"""search_docs tool: keyword search over README + docs tree only."""

from pathlib import Path

from issue_triage_agent.tools import make_search_docs


def _tree(root: Path) -> None:
    (root / "README.md").write_text("# Repo\nDark mode lives on the roadmap.\n")
    docs = root / "docs"
    (docs / "agents").mkdir(parents=True)
    (docs / "testing.md").write_text("Write a failing test first.\n")
    (docs / "agents" / "domain.md").write_text("Read the glossary first.\n")
    (root / "CONTEXT.md").write_text("Dark mode vocabulary.\n")
    src = root / "src"
    src.mkdir()
    (src / "app.py").write_text("# dark mode implementation\nprint('dark mode')\n")


def test_search_docs_returns_readme_and_docs_hits(tmp_path: Path) -> None:
    _tree(tmp_path)
    search_docs = make_search_docs(tmp_path)

    result = search_docs.invoke({"query": "dark mode"})

    assert isinstance(result, str)
    assert "README.md" in result
    assert "roadmap" in result


def test_search_docs_never_returns_source_files(tmp_path: Path) -> None:
    _tree(tmp_path)
    search_docs = make_search_docs(tmp_path)

    result = search_docs.invoke({"query": "dark mode"})

    assert isinstance(result, str)
    assert "src" not in result
    assert "app.py" not in result
    assert "CONTEXT.md" not in result


def test_search_docs_finds_nested_docs_hits(tmp_path: Path) -> None:
    _tree(tmp_path)
    search_docs = make_search_docs(tmp_path)

    result = search_docs.invoke({"query": "failing test"})

    assert isinstance(result, str)
    assert "testing.md" in result
    assert "failing test" in result


def test_search_docs_miss_reports_no_docs(tmp_path: Path) -> None:
    _tree(tmp_path)
    search_docs = make_search_docs(tmp_path)

    result = search_docs.invoke({"query": "quantum banana"})

    assert isinstance(result, str)
    assert "No docs found" in result
