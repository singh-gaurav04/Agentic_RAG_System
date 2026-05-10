from __future__ import annotations



from langgraph.graph import END, START, StateGraph

from src.graph.nodes import GraphNodes
from src.graph.state import AgentState
from src.schemas.agent_schema import AgentAction


def route_after_planner(state: AgentState) -> str:
    decision = state["planner_decision"]
    if decision is None:
        return "refusal_or_clarification"
    action = decision.get("action") if isinstance(decision, dict) else None
    if action in (AgentAction.ask_clarification.value, AgentAction.refuse.value):
        return "refusal_or_clarification"
    if action == AgentAction.answer.value:
        return "answer"
    if action == AgentAction.web_search.value:
        return "tool"
    if action in (
        AgentAction.retrieve_documents.value,
        AgentAction.rewrite_query.value,
        AgentAction.rerank_results.value,
    ):
        return "retrieval"
    return "refusal_or_clarification"


def route_after_retrieval(state: AgentState) -> str:
    """No corpus hits: fall back to web search for in-domain questions (planner allowed retrieval path)."""
    if len(state["retrieved_docs"]) == 0:
        return "tool"
    return "reranker"


def route_after_reranker(state: AgentState) -> str:
    decision = state["planner_decision"]
    action = decision.get("action") if isinstance(decision, dict) else None
    if action is None:
        return "answer"
    if action == AgentAction.web_search.value:
        return "tool"
    return "answer"


def build_graph(
    nodes: GraphNodes,
    checkpointer
):

    graph = StateGraph(AgentState)
    graph.add_node("planner", nodes.planner_node)
    graph.add_node("retrieval", nodes.retrieval_node)
    graph.add_node("reranker", nodes.reranker_node)
    graph.add_node("tool", nodes.tool_node)
    graph.add_node("answer", nodes.answer_node)
    graph.add_node("refusal_or_clarification", nodes.refusal_or_clarification_node)
    graph.add_node("evaluation_hook", nodes.evaluation_hook_node)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "retrieval": "retrieval",
            "tool": "tool",
            "answer": "answer",
            "refusal_or_clarification": "refusal_or_clarification",
        },
    )
    graph.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {
            "reranker": "reranker",
            "tool": "tool",
        },
    )
    graph.add_conditional_edges(
        "reranker",
        route_after_reranker,
        {
            "tool": "tool",
            "answer": "answer",
        },
    )
    graph.add_edge("tool", "answer")
    graph.add_edge("answer", "evaluation_hook")
    graph.add_edge("refusal_or_clarification", "evaluation_hook")
    graph.add_edge("evaluation_hook", END)
    return graph.compile(checkpointer=checkpointer)
