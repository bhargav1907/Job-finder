from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """All configuration comes from environment or backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider. Default is a local Ollama server: free, private, no API key.
    # Do NOT point this at a Claude Code / coding-plan endpoint. Those credentials
    # are licensed for approved harnesses only, not for application calls.
    llm_protocol: str = "ollama"  # "ollama" (local), "openai", or "anthropic"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str = "ollama"  # Ollama ignores the value, the SDK requires one
    llm_parse_model: str = "lfm3:1.7b"
    llm_rerank_model: str = "lfm3:1.7b"
    llm_fallback_model: str = "gemma4:12b"
    llm_timeout: float = 120.0

    # Storage
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'jobfinder.db'}"
    seed_path: Path = PROJECT_ROOT / "data" / "seed_jobs.json"

    # Retrieval
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    top_k: int = 40
    rerank_batch_size: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
