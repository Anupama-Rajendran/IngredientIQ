"""Configuration management for IngredientIQ backend."""
import os
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # LLM Config
    LLM_PROVIDER: str = "anthropic"  # anthropic, openai
    LLM_MODEL: str = "claude-3-sonnet-20240229"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # RAG Config
    VECTOR_DB_PATH: str = "./data/chroma"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    
    # API Endpoints
    OPEN_FOOD_FACTS_API: str = "https://world.openfoodfacts.org/api/v0/product"
    OPEN_BEAUTY_FACTS_API: str = "https://world.openbeautyfacts.org/api/v4/product"
    PUBCHEM_API: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # Backend Config
    DEBUG: bool = False
    BACKEND_PORT: int = 8000
    
    class Config:
        env_file = str(Path(__file__).parent / ".env")
        case_sensitive = True


settings = Settings()

# Debug: Log API key status on startup
if settings.ANTHROPIC_API_KEY:
    print("✅ ANTHROPIC_API_KEY is configured")
else:
    print("⚠️  WARNING: ANTHROPIC_API_KEY not found in .env file")
