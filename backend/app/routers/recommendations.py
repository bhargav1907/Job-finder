from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..config import get_settings
from ..db import get_session
from ..models import Resume
from ..schemas import JobRead, RecommendationItem, RecommendationList
from ..services.recommend import RecommendedJob, recommend_jobs as recommend
from ..services.retrieval import RETRIEVAL_VERSION, RetrievalFilters

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

    settings = get_settings()
    resolved_limit = limit or settings.final_top_k
    result = recommend(
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
        items=[_item(item) for item in result.items],
        items_without_salary=[_item(item) for item in result.items_without_salary],
        total=result.total,
        without_salary_total=result.without_salary_total,
        limit=resolved_limit,
        retrieval_version=RETRIEVAL_VERSION,
        rerank_status=result.rerank_status,
        rerank_version=result.rerank_version,
    )


def _item(item: RecommendedJob) -> RecommendationItem:
    return RecommendationItem(
        job=JobRead.model_validate(item.job),
        score=item.score,
        retrieval_score=item.retrieval_score,
        matched_skills=item.matched_skills,
        reasons=item.reasons,
        gaps=item.gaps,
        reranked=item.reranked,
    )
