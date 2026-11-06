"""Turn resume text into a validated, reconciled ATS profile."""

import re

import httpx
from pydantic import ValidationError

from ..config import get_settings
from ..llm.client import LLMClient, LLMError
from ..schemas import LLMParsedProfile, ResumeProfile
from .normalize import extract_skills, parse_salary

SYSTEM_PROMPT = """You extract structured profiles from resumes.
Copy facts exactly as written. Never invent a value.
Use "" for an absent string, null for an absent number, and [] for an absent list.
total_years_experience is the summed duration of all listed work, including internships,
in years. Salary figures are annual amounts in the currency implied by the resume:
multiply a monthly stipend by 12, and multiply an Indian LPA figure by 100000.
target_roles are job titles, never locations or sentences."""

_MONTHLY_RE = re.compile(r"(per\s+month|monthly|/\s*month|stipend)", re.IGNORECASE)


_FAILURES = (ValidationError, LLMError, httpx.HTTPError)


def parse_resume_text(
    text: str, *, client: LLMClient | None = None
) -> tuple[ResumeProfile, str]:
    client = client or LLMClient()
    settings = get_settings()
    primary = settings.llm_parse_model
    user = "RESUME:\n" + text

    try:
        parsed = _attempt(client, primary, user)
        return _reconcile(parsed, text), primary
    except ValidationError as exc:
        try:
            retry_prompt = f"{user}\n\nThe previous response failed validation: {exc}"
            parsed = _attempt(client, primary, retry_prompt)
            return _reconcile(parsed, text), primary
        except _FAILURES:
            pass
    except (LLMError, httpx.HTTPError):
        pass

    fallback = settings.llm_fallback_model
    if fallback and fallback != primary:
        try:
            parsed = _attempt(client, fallback, user)
            return _reconcile(parsed, text), fallback
        except _FAILURES:
            pass

    return _heuristic_profile(text), "heuristic-v1"


def _attempt(client: LLMClient, model: str, user: str) -> LLMParsedProfile:
    raw = client.complete_json(
        SYSTEM_PROMPT,
        user,
        model=model,
        max_tokens=2048,
        json_schema=LLMParsedProfile.model_json_schema(),
        purpose="parse",
    )
    return LLMParsedProfile.model_validate(raw)


def _heuristic_profile(text: str) -> ResumeProfile:
    salary_min, salary_max, currency = parse_salary(text)
    skills = extract_skills(text)
    return ResumeProfile(
        name="",
        email="",
        phone="",
        location="",
        summary="",
        total_years_experience=0,
        seniority="mid",
        target_roles=[],
        preferred_locations=[],
        remote_ok="remote" in text.lower(),
        salary_min=salary_min,
        salary_max=salary_max,
        currency=currency,
        skills=skills,
        canonical_skills=skills,
        experience=[],
        education=[],
        certifications=[],
        projects=[],
    )


def _reconcile(parsed: LLMParsedProfile, text: str) -> ResumeProfile:
    data = parsed.model_dump()

    det_min, det_max, det_currency = parse_salary(text)
    if det_min is not None:
        data["salary_min"], data["salary_max"], data["currency"] = (
            det_min,
            det_max,
            det_currency,
        )
    else:
        low, high = data["salary_min"], data["salary_max"]
        if low is not None and high is not None:
            if (
                _MONTHLY_RE.search(text)
                and data["currency"] == "INR"
                and max(low, high) < 200_000
            ):
                low, high = low * 12, high * 12
            if low < 0 or high < 0 or low > high:
                low = high = None
            data["salary_min"], data["salary_max"] = low, high
        elif low is not None or high is not None:
            value = low if low is not None else high
            if value < 0:
                data["salary_min"] = data["salary_max"] = None

    data["canonical_skills"] = extract_skills(text)
    return ResumeProfile(**data)
