"""Fake scripted LLM drives a ReAct-style tool loop, including search_docs."""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from issue_triage_agent.fakes.llm import ScriptedLLM
from issue_triage_agent.fakes.tools import make_search_docs


def test_scripted_llm_invokes_search_docs_then_finishes() -> None:
    search_docs, searches = make_search_docs(
        hits={"repro steps": ["docs/testing.md: write a failing test first"]}
    )
    model = ScriptedLLM(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_docs",
                        "args": {"query": "repro steps"},
                        "id": "call-1",
                    }
                ],
            ),
            AIMessage(content="See docs/testing.md for the repro-steps guidance."),
        ]
    )

    app = create_react_agent(model, [search_docs])
    result = app.invoke(
        {"messages": [("user", "How do I write repro steps?")]}
    )

    final = result["messages"][-1]
    assert isinstance(final, AIMessage)
    assert "docs/testing.md" in final.content
    assert searches == ["repro steps"]
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert "write a failing test first" in tool_messages[0].content


def test_scripted_llm_is_not_a_generic_fake() -> None:
    assert not isinstance(ScriptedLLM(messages=[]), GenericFakeChatModel)
