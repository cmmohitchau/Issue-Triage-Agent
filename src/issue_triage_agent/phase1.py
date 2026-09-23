"""Phase 1: ReAct loop from issue payload to proposal artifact (seam A)."""

import json
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from issue_triage_agent.artifact import ProposalArtifact
from issue_triage_agent.github_reads import GitHubReads
from issue_triage_agent.payload import IssuePayload
from issue_triage_agent.tools import (
    make_fetch_author_history,
    make_fetch_issue,
    make_search_docs,
)

TOOL_BUDGET = 10

#: Verbatim Issue Kind rubric: bug needs both repro evidence and environment.
NEEDS_REPRO_RUBRIC = (
    "kind = bug requires ALL of (a) reproduction steps OR verbatim error "
    "text/stack trace, and (b) environment info: app/package version AND "
    "OS/runtime. If either (a) or (b) is missing → kind = needs-repro. "
    "needs-repro means: a plausible bug, but the reporter must supply the "
    "missing item(s) before it can be worked."
)

SYSTEM_PROMPT = f"""You are an issue triage agent.
Call read-only tools in whatever order helps (fetch the issue, author history, etc.).
Issue Kind rubric (apply verbatim, never gut feeling):
{NEEDS_REPRO_RUBRIC}
Remaining kinds: feature, question, duplicate.
Acknowledge feature requests and questions warmly; confirm bugs per the rubric.
Tailor the draft to Author History: welcome first-time contributors, and
acknowledge repeat reporters with their prior issue count.
Link existing documentation via search_docs instead of retyping answers.
Fixed Triage Role mapping: needs-repro → needs-info; every other kind → needs-triage.
labels must include the issue_kind value and the triage_role value.
The draft must name exactly what is missing (repro steps or error text, version, OS/runtime).
When ready, emit a single JSON object with keys:
issue_kind, triage_role, duplicate, draft, labels, author_history.
No write tools exist; the JSON is your only output."""


def run_phase1(
    payload: IssuePayload,
    *,
    llm: BaseChatModel,
    github: GitHubReads,
    docs_root: Path | None = None,
) -> ProposalArtifact:
    """Run the ReAct triage loop for one opened issue; return the proposal artifact."""
    _ensure_issue_seeded(payload, github)
    tools = [
        make_fetch_issue(github),
        make_fetch_author_history(github),
        make_search_docs(docs_root),
    ]
    app = create_react_agent(llm, tools)
    result = app.invoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                ("user", f"Triage issue #{payload.number}: {payload.title}"),
            ]
        },
        config={"recursion_limit": TOOL_BUDGET * 2 + 1},
    )
    return _artifact_from_messages(result["messages"])


def _ensure_issue_seeded(payload: IssuePayload, github: GitHubReads) -> None:
    seed = getattr(github, "seed_issue", None)
    if seed is None:
        return
    seed(
        number=payload.number,
        title=payload.title,
        body=payload.body,
        author_login=payload.author_login,
        comments=list(payload.comments),
    )


def _artifact_from_messages(messages: list[BaseMessage]) -> ProposalArtifact:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            content = message.content
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            text = content.strip()
            if text.startswith("{"):
                return ProposalArtifact.model_validate(json.loads(text))
    raise ValueError("Phase 1 produced no JSON proposal artifact")
