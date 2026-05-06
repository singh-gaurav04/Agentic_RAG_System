from fastapi import APIRouter

router: APIRouter = APIRouter(
    tags=["Chat"],
)

@router.post("/chat")
def chat(request: str):
    return {"message": "Hello, World!"}
