"""Rerank retrieved jobs with the local model, in strictly validated batches."""

from dataclasses import dataclass
from typing import Literal

import httpx
from sqlmodel import Session

from ..config import get_settings
from ..llm.client import LLMClient, LLMError
from ..models import Job, Resume
from ..schemas import ResumeProfile

PROMPT_PREFIX = "rerank-v1"

RERANK_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "integer"},
                    "score": {"type": "integer"},
                    "reasons": {"type": "array", "items": {"type": "string"}},
                    "gaps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["job_id", "score", "reasons", "gaps"],
            },
        }
    },
    "required": ["results"],
}

SYSTEM_PROMPT = """You score how well a student fits each job.
Score fit from 0 to 100 using these bands:
80-100: strong fit — the required skills, seniority, and domain line up.
60-79: good fit — most requirements line up, one meaningful gap.
40-59: partial fit — the role or seniority is a stretch.
0-39: poor fit — wrong domain, skills, or seniority.
Judge seniority and domain honestly. Never invent facts that are not in the cards.
For every job give 1-3 concrete reasons and 1-3 gaps of at most one sentence each.
Return one entry per JOB id, with no extras and no duplicates."""


class RerankValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RerankResult:
    score: int
    reasons: list[str]
    gaps: list[str]
    reranked: bool


@dataclass(frozen=True)
class RerankOutcome:
    results: dict[int, RerankResult]
    status: Literal["ok", "partial", "unavailable"]


def prompt_version(model: str) -> str:
    return f"{PROMPT_PREFIX}@{model}"


def _job_card(job: Job) -> str:
    if job.salary_min is None and job.salary_max is None:
        salary = "not stated"
    else:
        low = job.salary_min if job.salary_min is not None else "-"
        high = job.salary_max if job.salary_max is not None else "-"
        salary = f"{low}-{high} {job.currency}"
    return (
        f"JOB {job.id}\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location} (remote: {'yes' if job.remote else 'no'})\n"
        f"Seniority: {job.seniority}\n"
        f"Salary: {salary}\n"
        f"Skills: {', '.join(job.skills) or 'none'}\n"
        f"Description: {job.description[:400]}"
    )


def _resume_card(profile: ResumeProfile) -> str:
    roles = "; ".join(profile.target_roles[:3]) or "none"
    locations = ", ".join(profile.preferred_locations[:3]) or "none"
    if profile.salary_min is None and profile.salary_max is None:
        salary = "not stated"
    else:
        low = profile.salary_min if profile.salary_min is not None else "-"
        high = profile.salary_max if profile.salary_max is not None else "-"
        salary = f"{low}-{high} {profile.currency}"
    skills = ", ".join(profile.canonical_skills[:12]) or "none"
    recent = "; ".join(role.title for role in profile.experience[:2]) or "none"
    card = (
        f"RESUME\n"
        f"Summary: {profile.summary[:200]}\n"
        f"Experience: {profile.total_years_experience} years, {profile.seniority}\n"
        f"Target roles: {roles}\n"
        f"Locations: {locations} (remote ok: {'yes' if profile.remote_ok else 'no'})\n"
        f"Salary expectation: {salary}\n"
        f"Skills: {skills}\n"
        f"Recent roles: {recent}"
    )
    return card[:800]


def _validate_batch(raw: object, requested_ids: set[int]) -> dict[int, RerankResult]:
    if not isinstance(raw, dict) or not isinstance(raw.get("results"), list):
        raise RerankValidationError("root must be an object with a results list")

    results: dict[int, RerankResult] = {}
    for entry in raw["results"]:
        if not isinstance(entry, dict):
            raise RerankValidationError("result entry must be an object")
        if any(key not in entry for key in ("job_id", "score", "reasons", "gaps")):
            raise RerankValidationError("result entry is missing a required key")

        job_id = entry["job_id"]
        if isinstance(job_id, bool) or not isinstance(job_id, int):
            raise RerankValidationError("job_id must be an integer")
        if job_id not in requested_ids:
            raise RerankValidationError(f"unknown job_id {job_id}")
        if job_id in results:
            raise RerankValidationError(f"duplicate job_id {job_id}")

        score = entry["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise RerankValidationError("score must be numeric")
        if not 0 <= score <= 100:
            raise RerankValidationError("score must be between 0 and 100")

        reasons = _clean_list(entry["reasons"], "reasons")
        gaps = _clean_list(entry["gaps"], "gaps")
        results[job_id] = RerankResult(
            score=round(score), reasons=reasons, gaps=gaps, reranked=True
        )

    missing = requested_ids - set(results)
    if missing:
        raise RerankValidationError(f"missing job ids: {sorted(missing)}")
    return results


def _clean_list(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise RerankValidationError(f"{name} must be a non-empty list")
    cleaned = []
    for item in value[:3]:
        if not isinstance(item, str) or not item.strip():
            raise RerankValidationError(f"{name} entries must be non-empty strings")
        cleaned.append(item.strip()[:200])
    return cleaned


def _degraded() -> RerankResult:
    return RerankResult(score=0, reasons=[], gaps=[], reranked=False)


def rerank_jobs(
    session: Session,
    resume: Resume,
    jobs: list[Job],
    *,
    client: LLMClient | None = None,
) -> RerankOutcome:
    if not jobs:
        return RerankOutcome(results={}, status="ok")

    settings = get_settings()
    client = client or LLMClient()
    model = settings.llm_rerank_model
    profile = ResumeProfile.model_validate(resume.profile)
    resume_card = _resume_card(profile)
    batch_size = settings.rerank_batch_size

    results: dict[int, RerankResult] = {}
    stopped = False
    for start in range(0, len(jobs), batch_size):
        batch = jobs[start : start + batch_size]
        if stopped:
            results.update({job.id: _degraded() for job in batch})
            continue

        user = resume_card + "\n\n" + "\n\n".join(_job_card(job) for job in batch)
        requested = {job.id for job in batch}
        try:
            batch_results = _attempt_batch(client, model, user, requested)
        except httpx.HTTPError:
            stopped = True
            batch_results = None

        if batch_results is None:
            results.update({job.id: _degraded() for job in batch})
        else:
            results.update(batch_results)

    reranked = sum(result.reranked for result in results.values())
    if reranked == len(results):
        status = "ok"
    elif reranked == 0:
        status = "unavailable"
    else:
        status = "partial"
    return RerankOutcome(results=results, status=status)


def _attempt_batch(
    client: LLMClient, model: str, user: str, requested: set[int]
) -> dict[int, RerankResult] | None:
    """One attempt, one retry; None when the batch is still unusable."""
    try:
        return _validate_batch(_call(client, model, user), requested)
    except (RerankValidationError, LLMError) as first_error:
        retry = f"{user}\n\nThe previous response failed validation: {first_error}"
        try:
            return _validate_batch(_call(client, model, retry), requested)
        except (RerankValidationError, LLMError):
            return None


def _call(client: LLMClient, model: str, user: str) -> object:
    return client.complete_json(
        SYSTEM_PROMPT,
        user,
        model=model,
        max_tokens=2048,
        json_schema=RERANK_SCHEMA,
        purpose="rerank",
    )
