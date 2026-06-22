"""
Application configuration using pydantic-settings.
Loads settings from .env file with sensible defaults.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # SMTP / Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./job_search.db"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Uploads
    UPLOAD_DIR: str = "./uploads"


# Singleton settings instance
settings = Settings()
