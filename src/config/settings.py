from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Skyclad Ventures Agentic Research System"

    #============= Google API Settings =============
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")
    google_gemini_model: str = Field(default="gemini-2.5-flash", env="GOOGLE_GEMINI_MODEL")
    google_gemini_embedding_model: str = Field(default="gemini-embedding-v1", env="GOOGLE_GEMINI_EMBEDDING_MODEL")

    #============= Mistral API Settings =============
    mistral_api_key: str = Field(default="", env="MISTRAL_API_KEY")
    mistral_model: str = Field(default="mistral-large-latest", env="MISTRAL_MODEL")
    mistral_embedding_model: str = Field(default="mistral-embedding-v1", env="MISTRAL_EMBEDDING_MODEL")

    #============= Vector Database Settings =============
    pinecone_api_key: str = Field(default="", env="PINECONE_API_KEY")
    pinecone_index: str = Field(default="skyclad", env="PINECONE_INDEX")
    pinecone_namespace: str = "default"
    top_k_final: int = Field(default=10, env="TOP_K_FINAL")

    #============= Storage Settings =============
    raw_pdf_dir: str = str(Path("storage") / "pdfs")

    #============= Retrieval Settings =============
    min_retrieval_score: float = Field(default=0.2, ge=0.0, le=1.0)

@lru_cache
def get_settings() -> Settings:
    return Settings()

    