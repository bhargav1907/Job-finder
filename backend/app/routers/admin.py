from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ..config import get_settings
from ..db import get_session
from ..schemas import IngestStats
from ..services.ingest import ingest_raw
from ..sources.base import JobQuery
from ..sources.seed import SeedSource

router = APIRouter()


@router.post("/admin/ingest", response_model=IngestStats)
def ingest_seed(
    embed: bool = Query(True, description="Compute missing embeddings after insert"),
    session: Session = Depends(get_session),
) -> IngestStats:
    settings = get_settings()
    raw_jobs = SeedSource(settings.seed_path).fetch(JobQuery())
    result = ingest_raw(session, raw_jobs, embed=embed)
    return IngestStats(**result.as_dict())
