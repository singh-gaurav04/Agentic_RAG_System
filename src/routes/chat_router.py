from fastapi import APIRouter, HTTPException
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from src.graph.state import AgentState
from src.routes.dependencies import get_graph
from langchain_core.messages import HumanMessage
from src.schemas.agent_schema import AgentAction, ChatRequest, ChatResponse, PlannerDecision, Reference

from rich import print

router: APIRouter = APIRouter(
    tags=["Chat"],
)


@router.post("/chat")
async def chat(request: ChatRequest):

    graph = get_graph()
    

    initial_state: AgentState = {
        "session_id": request.session_id,
        "session_title": "New chat",
        "user_query": request.user_query,
        "messages": [HumanMessage(content=request.user_query)],
        "planner_decision": None,
        "rewritten_query": None,
        "retrieved_docs": [],
        "references": [],
        "tool_outputs": [],
        "intermediate_reasoning": [],
        "confidence_signals": {},
        "final_answer": "",
        "traces": [],
    }

    try:
        config: RunnableConfig = {"configurable": {"thread_id": request.session_id}}
        result_state = await graph.ainvoke(initial_state, config)

   
    except Exception as exception:
        raise HTTPException(status_code=500, detail=str(exception)) from exception

    response_action = result_state["planner_decision"]["action"]
    response_confidence = result_state["planner_decision"]["confidence"]

    validated_references = [Reference.model_validate(item) for item in result_state["references"]]
    session_title = result_state["session_title"]

    return ChatResponse(
        session_id=request.session_id,
        session_title=session_title,
        answer=result_state["final_answer"],
        action=response_action,
        confidence=response_confidence,
        references=validated_references,
        traces=result_state["traces"],
    )
