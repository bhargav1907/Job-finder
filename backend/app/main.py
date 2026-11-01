from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import admin, jobs


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="FLA Job Finder", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(admin.router, prefix="/api", tags=["admin"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/llm")
def llm_health() -> dict:
    """Reports whether the local model server is reachable and which models it has."""
    import httpx

    settings = get_settings()
    base = settings.llm_base_url.removesuffix("/v1")
    try:
        response = httpx.get(f"{base}/api/tags", timeout=3.0)
        response.raise_for_status()
        names = [model.get("name") for model in response.json().get("models", [])]
        return {"reachable": True, "base_url": settings.llm_base_url, "models": names}
    except Exception as exc:  # noqa: BLE001 - health endpoint reports, never raises
        return {"reachable": False, "base_url": settings.llm_base_url, "error": str(exc)}
