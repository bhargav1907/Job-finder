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
    llm_parse_model: str = "qwen3:4b"
    llm_rerank_model: str = "lfm3:1.7b"
    # Small fallback, loaded only when the primary returns invalid JSON.
    # Set to "" to disable and rely on a same-model repair retry.
    llm_fallback_model: str = "llama3.2:3b"
    llm_timeout: float = 120.0
    # Cap Ollama's context window so large defaults do not blow up memory.
    llm_num_ctx: int = 8192

    # Optional rerank-only provider overrides. Empty values inherit the global
    # provider above, so the default stays fully local: parsing and reranking
    # can use different providers.
    llm_rerank_protocol: str = ""
    llm_rerank_base_url: str = ""
    llm_rerank_api_key: str = ""
    llm_rerank_timeout: float = 30.0

    # Storage
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'jobfinder.db'}"
    seed_path: Path = PROJECT_ROOT / "data" / "seed_jobs.json"
    boards_path: Path = PROJECT_ROOT / "data" / "boards.json"

    # Resume upload
    resume_max_bytes: int = 5 * 1024 * 1024
    resume_max_chars: int = 50_000

    # Retrieval
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    top_k: int = 40
    # Only this many candidates per salary bucket reach the reranker. The rest
    # keep their retrieval score, which caps hosted token cost per search.
    rerank_top_per_bucket: int = 20
    # Short cards keep the rerank prompt inside a hosted free tier's token cap.
    rerank_description_chars: int = 200
    rerank_batch_size: int = 10
    final_top_k: int = 30
    unstated_target_share: float = 0.3333
    rerank_llm_weight: float = 0.7


@lru_cache
def get_settings() -> Settings:
    return Settings()
