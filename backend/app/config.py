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

    # LLM provider (BytePlus Ark is Anthropic-compatible for Claude Code;
    # switch to "openai" if your Ark app key uses the OpenAI protocol).
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.ap-southeast.bytepluses.com/api"
    llm_protocol: str = "anthropic"
    llm_parse_model: str = "dola-seed-2.0-lite"
    llm_rerank_model: str = "dola-seed-2.0-lite"
    llm_fallback_model: str = "deepseek-v4.1-flash"

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
