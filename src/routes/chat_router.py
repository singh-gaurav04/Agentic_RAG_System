from fastapi import APIRouter
from src.schemas.agent_schema import ChatRequest

router: APIRouter = APIRouter(
    tags=["Chat"],
)

@router.post("/chat")
def chat(request: ChatRequest):
    return {"message": "Hello, World!"}
