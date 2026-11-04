import os

import pytest

from app.schemas import ResumeProfile
from app.services.resume_parse import parse_resume_text

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_TESTS") != "1", reason="set RUN_LLM_TESTS=1 to call the local model"
)

RESUMES = [
    ("junior", "Priya Sharma, data scientist, Python, LangChain. Expected 14-18 LPA."),
    ("fresher", "Arjun Mehta, final-year student. Python, SQL. Stipend 25,000-35,000 per month."),
    ("senior", "Rahul Verma, senior backend engineer, Python, Go. Expected 30-40 LPA."),
]


@pytest.mark.parametrize("label,text", RESUMES)
def test_qwen3_returns_a_valid_profile(label, text):
    profile, model = parse_resume_text(text)
    assert isinstance(profile, ResumeProfile)
    assert model == "qwen3:4b"
    assert profile.salary_min is not None and profile.salary_max is not None
    assert profile.salary_min >= 100_000  # annual, never a raw monthly stipend
