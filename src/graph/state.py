from __future__ import annotations

from typing import TypedDict

from src.schemas.agent_schema import ChatRequest, ChatResponse, Reference, PlannerDecision, RetrievedDocument,ChatMessage

#==================Agent State==================

class AgentState(TypedDict):
    session_id: str
    chat_request: str
    conversation_history: list[ChatMessage]
    memory_summary: str
    planner_decision: PlannerDecision | None
    rewritten_query: str | None
    retrieved_docs: list[RetrievedDocument]
    references: list[Reference]
    tool_outputs: list[dict[str, object]]
    intermediate_reasoning: list[str]
    confidence_signals: dict[str, float]
    final_answer: str
    traces: list[dict[str, object]]
