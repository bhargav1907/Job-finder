"""Deterministic job retrieval: hard filters plus local embedding similarity.

No LLM is involved. The output is a candidate pool for M4's reranker, not a
fit score the UI should present as a final answer.
"""

from dataclasses import dataclass
from datetime import timezone

import numpy as np
from sqlalchemy import or_
from sqlmodel import Session, select

from ..embeddings import embed_texts, from_bytes, to_bytes
from ..models import Job, Resume
from ..schemas import ResumeProfile
from .normalize import infer_role_family
from .resumes import resume_embed_text

SEMANTIC_WEIGHT = 0.85
SKILL_WEIGHT = 0.15
RETRIEVAL_VERSION = "v1"
DEFAULT_LIMIT = 40


@dataclass(frozen=True)
class RetrievalFilters:
    location: str | None = None
    remote: bool | None = None
    experience_years: int | None = None
    role: str | None = None
    salary_min: int | None = None


@dataclass(frozen=True)
class Candidate:
    job: Job
    score: float
    matched_skills: list[str]


@dataclass(frozen=True)
class RetrievalResult:
    items: list[Candidate]
    items_without_salary: list[Candidate]
    total: int
    without_salary_total: int


def retrieve_jobs(
    session: Session,
    resume: Resume,
    *,
    filters: RetrievalFilters | None = None,
    limit: int = DEFAULT_LIMIT,
) -> RetrievalResult:
    """Rank jobs for one resume. Filters are hard only when explicitly supplied."""
    filters = filters or RetrievalFilters()
    profile = ResumeProfile.model_validate(resume.profile)
    resume_vector = _resume_vector(session, resume, profile)
    resume_currency = (profile.currency or "INR").upper()

    stmt = select(Job).where(Job.embedding.is_not(None))
    stmt = _apply_filters(stmt, filters)
    jobs = session.exec(stmt).all()

    paid: list[Candidate] = []
    unknown: list[Candidate] = []
    for job in jobs:
        job_vector = from_bytes(job.embedding)
        if job_vector.shape[0] != resume_vector.shape[0]:
            continue

        semantic = max(0.0, float(np.dot(job_vector, resume_vector)))
        job_skills = list(job.skills or [])
        matched_skills = sorted(set(profile.canonical_skills) & set(job_skills))
        skill_share = len(matched_skills) / len(job_skills) if job_skills else 0.0
        score = round(SEMANTIC_WEIGHT * semantic + SKILL_WEIGHT * skill_share, 4)
        candidate = Candidate(job=job, score=score, matched_skills=matched_skills)

        if filters.salary_min is None:
            paid.append(candidate)
        elif salary_is_unknown(job, resume_currency):
            unknown.append(candidate)
        elif job.salary_max >= filters.salary_min:
            paid.append(candidate)

    paid.sort(key=_sort_key)
    unknown.sort(key=_sort_key)
    return RetrievalResult(
        items=paid[:limit],
        items_without_salary=unknown[:limit],
        total=len(paid),
        without_salary_total=len(unknown),
    )


def salary_is_unknown(job: Job, currency: str) -> bool:
    return (
        job.salary_min is None
        or job.salary_max is None
        or (job.currency or "").upper() != currency
    )


def _apply_filters(stmt, filters: RetrievalFilters):
    if filters.location:
        matches = Job.location.ilike(_like(filters.location), escape="\\")
        if filters.location.strip().lower() == "remote":
            matches = or_(matches, Job.remote.is_(True))
        stmt = stmt.where(matches)
    if filters.remote is not None:
        stmt = stmt.where(Job.remote.is_(filters.remote))
    if filters.experience_years is not None:
        stmt = stmt.where(Job.seniority.in_(seniority_levels(filters.experience_years)))
    if filters.role:
        family = infer_role_family(filters.role)
        if family == "other":
            stmt = stmt.where(Job.title.ilike(_like(filters.role), escape="\\"))
        else:
            stmt = stmt.where(Job.role_family == family)
    return stmt


def _like(term: str) -> str:
    term = term.strip()
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def seniority_levels(years: int) -> tuple[str, ...]:
    if years <= 0:
        return ("intern", "junior")
    if years <= 2:
        return ("junior", "mid")
    if years <= 5:
        return ("mid", "senior")
    return ("senior", "lead")


def _resume_vector(session: Session, resume: Resume, profile: ResumeProfile) -> np.ndarray:
    if resume.embedding:
        return from_bytes(resume.embedding)

    vector = embed_texts([resume_embed_text(profile)])[0]
    resume.embedding = to_bytes(vector)
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return from_bytes(resume.embedding)


def _posted_timestamp(job: Job) -> float:
    posted = job.posted_at
    if posted is None:
        return float("-inf")
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    return posted.timestamp()


def _sort_key(candidate: Candidate) -> tuple[float, float, int]:
    return (-candidate.score, -_posted_timestamp(candidate.job), candidate.job.id or 0)
