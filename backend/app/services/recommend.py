"""Blend retrieval and rerank scores, then pick a salary-balanced final list."""

from dataclasses import dataclass
from datetime import timezone

from sqlmodel import Session

from ..config import get_settings
from ..llm.client import LLMClient
from ..models import Job, Resume
from ..schemas import ResumeProfile
from .rerank import prompt_version, rerank_jobs
from .retrieval import Candidate, RetrievalFilters, retrieve_jobs, salary_is_unknown


@dataclass(frozen=True)
class RecommendedJob:
    job: Job
    retrieval_score: float
    score: float
    matched_skills: list[str]
    reasons: list[str]
    gaps: list[str]
    reranked: bool


@dataclass(frozen=True)
class RecommendationResult:
    items: list[RecommendedJob]
    items_without_salary: list[RecommendedJob]
    total: int
    without_salary_total: int
    rerank_status: str
    rerank_version: str


def blend_score(llm_score: int, retrieval_score: float, weight: float) -> float:
    blended = weight * llm_score + (1 - weight) * retrieval_score * 100
    return round(min(max(blended, 0.0), 100.0), 1)


def recommend_jobs(
    session: Session,
    resume: Resume,
    *,
    filters: RetrievalFilters | None = None,
    limit: int | None = None,
    client: LLMClient | None = None,
) -> RecommendationResult:
    settings = get_settings()
    limit = limit if limit is not None else settings.final_top_k
    retrieved = retrieve_jobs(session, resume, filters=filters, limit=settings.top_k)
    candidates = _dedupe(retrieved.items + retrieved.items_without_salary)
    outcome = rerank_jobs(session, resume, [c.job for c in candidates], client=client)

    profile = ResumeProfile.model_validate(resume.profile)
    currency = (profile.currency or "INR").upper()
    known: list[RecommendedJob] = []
    unstated: list[RecommendedJob] = []
    for candidate in candidates:
        rerank_result = outcome.results[candidate.job.id]
        if rerank_result.reranked:
            score = blend_score(
                rerank_result.score, candidate.score, settings.rerank_llm_weight
            )
            reasons = list(rerank_result.reasons)
            gaps = list(rerank_result.gaps)
        else:
            score = round(candidate.score * 100, 1)
            reasons, gaps = [], []
        item = RecommendedJob(
            job=candidate.job,
            retrieval_score=round(candidate.score, 4),
            score=score,
            matched_skills=list(candidate.matched_skills),
            reasons=reasons,
            gaps=gaps,
            reranked=rerank_result.reranked,
        )
        if salary_is_unknown(candidate.job, currency):
            unstated.append(item)
        else:
            known.append(item)

    known.sort(key=_sort_key)
    unstated.sort(key=_sort_key)
    known_target, unstated_target = _targets(
        limit, len(known), len(unstated), settings.unstated_target_share
    )
    return RecommendationResult(
        items=known[:known_target],
        items_without_salary=unstated[:unstated_target],
        total=len(known),
        without_salary_total=len(unstated),
        rerank_status=outcome.status,
        rerank_version=prompt_version(settings.llm_rerank_model),
    )


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    seen: set[int] = set()
    unique = []
    for candidate in candidates:
        if candidate.job.id in seen:
            continue
        seen.add(candidate.job.id)
        unique.append(candidate)
    return unique


def _targets(limit: int, known: int, unstated: int, share: float) -> tuple[int, int]:
    unstated_target = min(round(limit * share), unstated)
    known_target = min(limit - unstated_target, known)
    leftover = limit - known_target - unstated_target
    if leftover > 0:
        unstated_target += min(leftover, unstated - unstated_target)
    return known_target, unstated_target


def _sort_key(item: RecommendedJob) -> tuple[float, float, float, int]:
    return (
        -item.score,
        -item.retrieval_score,
        -_posted_timestamp(item.job),
        item.job.id or 0,
    )


def _posted_timestamp(job: Job) -> float:
    posted = job.posted_at
    if posted is None:
        return float("-inf")
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    return posted.timestamp()
