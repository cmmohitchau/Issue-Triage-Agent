"""Read-only agent tools with injectable boundaries for tests."""

from langchain_core.tools import BaseTool, tool


def make_search_docs(
    hits: dict[str, list[str]] | None = None,
) -> tuple[BaseTool, list[str]]:
    """Build a search_docs tool over README/docs hits; returns (tool, queries seen)."""
    table = hits or {}
    seen: list[str] = []

    @tool
    def search_docs(query: str) -> str:
        """Keyword search over the README and docs tree; returns top hits."""
        seen.append(query)
        results = table.get(query, [])
        if not results:
            return f"No docs found for {query!r}."
        return "\n".join(results)

    return search_docs, seen
