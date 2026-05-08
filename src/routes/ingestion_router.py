from fastapi import APIRouter,status,HTTPException

from src.schemas.agent_schema import IngestRequest, IngestResponse
from src.routes.dependencies import get_ingestor

router: APIRouter = APIRouter(
    tags=["For Admin-Ingestion"],
)
#==================Ingest Papers==================
@router.post("/ingest-papers")
async def ingest_papers(request: IngestRequest):
    if request.max_papers > 200:
        raise HTTPException(status_code=400, detail="Maximum number of papers to ingest is 200")
    if request.max_papers < 1:
        raise HTTPException(status_code=400, detail="Minimum number of papers to ingest is 1")
    if request.category not in ["cs.AI", "cs.CV", "cs.LG", "cs.CL", "cs.SE", "cs.DS"]:
        raise HTTPException(status_code=400, detail="Invalid category")
    if request.days_back > 365:
        raise HTTPException(status_code=400, detail="Maximum number of days back to ingest papers is 365")
    if request.days_back < 1:
        raise HTTPException(status_code=400, detail="Minimum number of days back to ingest papers is 1")
    if request.batch_size > 50:
        raise HTTPException(status_code=400, detail="Maximum number of papers to ingest in each batch is 50")
    if request.batch_size < 1:
        raise HTTPException(status_code=400, detail="Minimum number of papers to ingest in each batch is 1")

    ingestor = get_ingestor()
    response : IngestResponse = await ingestor.ingest_paper(request)
    return response