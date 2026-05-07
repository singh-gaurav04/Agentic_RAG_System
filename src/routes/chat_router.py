from fastapi import APIRouter
from src.schemas.agent_schema import ChatRequest
from src.graph.state import AgentState
# from src.graph.graph import get_graph

router: APIRouter = APIRouter(
    tags=["Chat"],
)

@router.post("/chat")
async def chat(request: ChatRequest):

    #==================Initialize Graph==================
    
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

