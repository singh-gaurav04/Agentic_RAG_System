from fastapi import APIRouter, HTTPException
from src.schemas.agent_schema import ChatRequest, ChatResponse, AgentAction
from src.graph.state import AgentState
from src.routes.dependencies import get_graph


router: APIRouter = APIRouter(
    tags=["Chat"],
)

@router.post("/chat")
async def chat(request: ChatRequest):

    #==================Initialize Graph==================

    graph = get_graph()
    
    #==================Initialize Agent State==================
    initial_state: AgentState = {
        "session_id": request.session_id,
        "user_query": request.user_query,
        "conversation_history": request.history,
        "memory_summary": "",
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
        result_state = await graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    planner_decision = result_state["planner_decision"]
    return ChatResponse(
        session_id=request.session_id,
        answer=result_state["final_answer"],
        action=planner_decision.action if planner_decision else AgentAction.answer,
        confidence=planner_decision.confidence if planner_decision else 0.0,
        references=result_state["references"],
        traces=result_state["traces"],
    )