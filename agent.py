"""A Deep Agents agent on a scripted fake chat model, traced through LangSmith's OpenTelemetry
mode and exported to `reede serve`. No API key, no model network call, nothing goes to LangSmith.

Real model: set REEDE_EXAMPLE_BASE_URL, REEDE_EXAMPLE_API_KEY and REEDE_EXAMPLE_MODEL (any
OpenAI-compatible endpoint) and `pip install langchain-openai`. See the README.
"""
import reede_otel

reede_otel.configure()  # must run before langchain/langgraph are imported

import os
from typing import Any, List, Optional

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool


@tool
def lookup(topic: str) -> str:
    """Look up a short fact about a topic."""
    return f"{topic}: a reported receipt proves what the agent reported and when it was sealed."


class FakeChat(BaseChatModel):
    """Calls `lookup` once, then answers. Reports token usage like a real provider."""

    @property
    def _llm_type(self) -> str:
        return "fake-chat"

    def bind_tools(self, tools: Any, **kw: Any) -> "FakeChat":
        return self

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Any = None, **kw: Any) -> ChatResult:
        usage = {"input_tokens": 12, "output_tokens": 7, "total_tokens": 19}
        if any(isinstance(m, ToolMessage) for m in messages):
            msg = AIMessage(content="Done: " + str(messages[-1].content), usage_metadata=usage)
        else:
            call = {"name": "lookup", "args": {"topic": "reported receipts"}, "id": "call_1", "type": "tool_call"}
            msg = AIMessage(content="", tool_calls=[call], usage_metadata=usage)
        return ChatResult(generations=[ChatGeneration(message=msg)])


def make_model():
    if os.environ.get("REEDE_EXAMPLE_BASE_URL"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            base_url=os.environ["REEDE_EXAMPLE_BASE_URL"],
            api_key=os.environ["REEDE_EXAMPLE_API_KEY"],
            model=os.environ["REEDE_EXAMPLE_MODEL"],
        )
    return FakeChat()


agent = create_deep_agent(model=make_model(), tools=[lookup], system_prompt="Use lookup, then answer briefly.")

if __name__ == "__main__":
    out = agent.invoke({"messages": [{"role": "user", "content": "What does a reported receipt prove?"}]})
    print(out["messages"][-1].content)
    from langsmith import Client

    Client().flush()
    from opentelemetry import trace

    provider = trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
