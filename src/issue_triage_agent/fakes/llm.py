"""Scripted LLM at the model network boundary for seam A tests."""

from collections.abc import Sequence
from typing import Self

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedLLM(BaseChatModel):
    """Replays a fixed script of assistant messages, including tool calls."""

    messages: Sequence[AIMessage]

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: object, **kwargs: object) -> Self:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        if not self.messages:
            msg = messages[-1].content if messages else ""
            raise RuntimeError(f"ScriptedLLM exhausted; last message: {msg!r}")
        script = list(self.messages)
        next_message = script[0]
        object.__setattr__(self, "messages", tuple(script[1:]))
        return ChatResult(generations=[ChatGeneration(message=next_message)])
