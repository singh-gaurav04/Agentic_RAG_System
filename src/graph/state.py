from __future__ import annotations

from typing import Any, TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# Serializable checkpoint state: primitives, dict/list, traces only.
# Structured domain objects round-trip via Pydantic model_dump(mode="json") / model_validate.


class AgentState(TypedDict):
    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]

    session_title: str | None = None
    session_id: str
    user_query: str
    planner_decision: dict[str, Any] | None

    rewritten_query: str | None
    retrieved_docs: list[dict[str, Any]]
    references: list[dict[str, Any]]
    tool_outputs: list[dict[str, Any]]
    intermediate_reasoning: list[str]
    confidence_signals: dict[str, float]
    final_answer: str
    traces: list[dict[str, Any]]
