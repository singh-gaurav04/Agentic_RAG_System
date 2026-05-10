from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes.chat_router import router as chat_router
from src.routes.health_router import router as health_router
from src.routes.ingestion_router import router as ingestion_router
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Skyclad Ventures Agentic Research System",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router)
app.include_router(health_router)
app.include_router(chat_router)
