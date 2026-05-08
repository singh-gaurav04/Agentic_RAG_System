from src.graph.state import AgentState
from src.schemas.agent_schema import AgentAction

from langgraph.graph import StateGraph,START,END

from src.graph.nodes import GraphNodes


def route_after_planner(state: AgentState) -> str:
    decision = state["planner_decision"]
    if decision is None:
        return "refusal_or_clarification"
    if decision.action in {AgentAction.ask_clarification, AgentAction.refuse}:
        return "refusal_or_clarification"
    if decision.action == AgentAction.answer:
        return "answer"
    if decision.action == AgentAction.web_search:
        return "tool"
    if decision.action == AgentAction.rewrite_query:
        return "retrieval"
    return "retrieval"


def route_after_retrieval(state: AgentState) -> str:
    if state["retrieved_docs"]:
        return "reranker"
    return "refusal_or_clarification"

def build_graph(nodes: GraphNodes):

    graph = StateGraph(AgentState)

    graph.add_node("planner", nodes.planner_node)
    graph.add_node("memory", nodes.load_memory_node)
    graph.add_node("planner", nodes.planner_node)
    graph.add_node("retrieval", nodes.retrieval_node)
    graph.add_node("reranker", nodes.reranker_node)
    graph.add_node("tool", nodes.tool_node)
    graph.add_node("answer", nodes.answer_node)
    graph.add_node("refusal_or_clarification", nodes.refusal_or_clarification_node)
    graph.add_node("evaluation_hook", nodes.evaluation_hook_node)
    graph.add_edge(START, "memory")
    graph.add_edge("memory", "planner")

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "retrieval": "retrieval",
            "tool": "tool",
            "answer": "answer",
            "refusal_or_clarification": "refusal_or_clarification",
        }
    )

    graph.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {
            "reranker": "reranker",
            "refusal_or_clarification": "refusal_or_clarification",
        }
    )

    graph.add_edge("reranker", "tool")
    graph.add_edge("tool", "answer")
    graph.add_edge("answer", "evaluation_hook")
    graph.add_edge("refusal_or_clarification", "evaluation_hook")
    graph.add_edge("evaluation_hook", END)

    return graph.compile()


