"""Turn resume text into a validated, reconciled ATS profile."""

import re

from ..config import get_settings
from ..llm.client import LLMClient
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


def parse_resume_text(
    text: str, *, client: LLMClient | None = None
) -> tuple[ResumeProfile, str]:
    client = client or LLMClient()
    settings = get_settings()
    raw = client.complete_json(
        SYSTEM_PROMPT,
        "RESUME:\n" + text,
        model=settings.llm_parse_model,
        max_tokens=2048,
        json_schema=LLMParsedProfile.model_json_schema(),
    )
    parsed = LLMParsedProfile.model_validate(raw)
    return _reconcile(parsed, text), settings.llm_parse_model


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
