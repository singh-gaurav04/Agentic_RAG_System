from fastapi import FastAPI, APIRouter
from src.routes.chat_router import router as chat_router
from src.routes.health_router import router as health_router
from src.routes.ingestion_router import router as ingestion_router

app = FastAPI(
    title="Skyclad Ventures Agentic Research System",
)

app.include_router(ingestion_router)


app.include_router(health_router)
app.include_router(chat_router)
