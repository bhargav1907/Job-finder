import pytest
from pydantic import ValidationError

from app.schemas import LLMParsedProfile
from app.services.resume_parse import parse_resume_text
from tests.factories import FULL_PROFILE


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete_json(self, system, user, *, model, max_tokens, json_schema=None):
        self.calls.append((model, json_schema))
        if not self.responses:
            raise AssertionError("unexpected extra LLM call")
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_returns_validated_profile_and_model():
    client = FakeClient([FULL_PROFILE])
    profile, model = parse_resume_text("Expected 14-18 LPA", client=client)
    assert model == "qwen3:4b"
    assert profile.name == "Priya Sharma"
    assert profile.experience[0].company == "Acme"
    assert client.calls[0][0] == "qwen3:4b"
    assert client.calls[0][1]["required"]


def test_lpa_is_reconciled_deterministically():
    profile, _ = parse_resume_text("Expected 14-18 LPA", client=FakeClient([FULL_PROFILE]))
    assert (profile.salary_min, profile.salary_max, profile.currency) == (
        1_400_000,
        1_800_000,
        "INR",
    )


def test_monthly_stipend_is_annualized():
    monthly = dict(FULL_PROFILE, salary_min=25_000, salary_max=35_000)
    profile, _ = parse_resume_text(
        "Stipend 25,000-35,000 per month", client=FakeClient([monthly])
    )
    assert (profile.salary_min, profile.salary_max) == (300_000, 420_000)


def test_inverted_salary_is_discarded():
    inverted = dict(FULL_PROFILE, salary_min=900_000, salary_max=500_000)
    profile, _ = parse_resume_text("No salary stated", client=FakeClient([inverted]))
    assert profile.salary_min is None and profile.salary_max is None


def test_canonical_skills_come_from_the_text():
    text = "Skills: Python, SQL, pandas, LangChain, Docker"
    profile, _ = parse_resume_text(text, client=FakeClient([dict(FULL_PROFILE, skills=[])]))
    assert set(profile.canonical_skills) >= {"python", "sql", "pandas", "langchain", "docker"}


def test_all_profile_fields_are_required():
    partial = {k: v for k, v in FULL_PROFILE.items() if k != "summary"}
    with pytest.raises(ValidationError):
        LLMParsedProfile.model_validate(partial)
