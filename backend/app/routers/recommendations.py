from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..config import get_settings
from ..db import get_session
from ..models import Resume
from ..schemas import JobRead, RecommendationItem, RecommendationList
from ..services.retrieval import (
    RETRIEVAL_VERSION,
    Candidate,
    RetrievalFilters,
    retrieve_jobs,
)

router = APIRouter()


@router.get("/resumes/{resume_id}/recommendations", response_model=RecommendationList)
def recommend_jobs(
    resume_id: int,
    location: str | None = None,
    remote: bool | None = None,
    experience_years: int | None = Query(None, ge=0, le=60),
    role: str | None = None,
    salary_min: int | None = Query(None, ge=0),
    limit: int | None = Query(None, ge=1, le=100),
    session: Session = Depends(get_session),
) -> RecommendationList:
    resume = session.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    resolved_limit = limit or get_settings().top_k
    result = retrieve_jobs(
        session,
        resume,
        filters=RetrievalFilters(
            location=location,
            remote=remote,
            experience_years=experience_years,
            role=role,
            salary_min=salary_min,
        ),
        limit=resolved_limit,
    )
    return RecommendationList(
        resume_id=resume_id,
        items=[_item(candidate) for candidate in result.items],
        items_without_salary=[
            _item(candidate) for candidate in result.items_without_salary
        ],
        total=result.total,
        without_salary_total=result.without_salary_total,
        limit=resolved_limit,
        retrieval_version=RETRIEVAL_VERSION,
    )


def _item(candidate: Candidate) -> RecommendationItem:
    return RecommendationItem(
        job=JobRead.model_validate(candidate.job),
        score=candidate.score,
        matched_skills=candidate.matched_skills,
    )
