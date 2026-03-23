"""Configuration management for IngredientIQ backend."""
import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = ConfigDict(
        extra='ignore',  # Ignore extra environment variables
        env_file=str(Path(__file__).parent / ".env"),
        case_sensitive=True
    )
    
    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # LLM Config
    LLM_PROVIDER: str = "anthropic"  # anthropic, openai
    LLM_MODEL: str = "claude-haiku-4-5-20251001"  # Production LLM for answer generation
    LM_MODEL: Optional[str] = None  # Alias for LLM_MODEL from env
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


settings = Settings()

# Debug: Log API key status on startup
if settings.ANTHROPIC_API_KEY:
    print("[OK] ANTHROPIC_API_KEY is configured")
else:
    print("[WARN] WARNING: ANTHROPIC_API_KEY not found in .env file")
