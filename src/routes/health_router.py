from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router: APIRouter = APIRouter(
    tags=["Home"],
)

@router.get("/health")
def health_check():
    return {"status": "ok"}
