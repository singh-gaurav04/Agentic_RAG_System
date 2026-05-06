from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

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
    pinecone_index: str = Field(default="skyclad-research-index", env="PINECONE_INDEX")

@lru_cache
def get_settings() -> Settings:
    return Settings()

    