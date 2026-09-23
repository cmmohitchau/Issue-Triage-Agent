"""Fakes at the network boundaries for seam A and seam B tests."""

from issue_triage_agent.fakes.github import FakeGitHub, WriteCall, WriteOp
from issue_triage_agent.fakes.llm import ScriptedLLM
from issue_triage_agent.fakes.tools import make_search_docs

__all__ = ["FakeGitHub", "ScriptedLLM", "WriteCall", "WriteOp", "make_search_docs"]
