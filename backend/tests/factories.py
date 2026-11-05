from datetime import datetime, timezone
from itertools import count

from app.models import Job
from app.schemas import ResumeProfile

_job_counter = count(1)

FULL_PROFILE = {
    "name": "Priya Sharma",
    "email": "priya@example.com",
    "phone": "+91 98765 43210",
    "location": "Bengaluru",
    "summary": "Junior data scientist.",
    "total_years_experience": 1.5,
    "seniority": "junior",
    "target_roles": ["data scientist"],
    "preferred_locations": ["Bengaluru", "remote"],
    "remote_ok": True,
    "salary_min": 14,
    "salary_max": 18,
    "currency": "INR",
    "skills": ["Python", "LangChain"],
    "experience": [
        {
            "title": "Data Scientist",
            "company": "Acme",
            "start": "2025",
            "end": "present",
            "highlights": [],
        }
    ],
    "education": [{"degree": "B.Tech", "institution": "VIT", "year": "2024"}],
    "certifications": [],
    "projects": [],
}


def make_profile() -> ResumeProfile:
    return ResumeProfile(**FULL_PROFILE, canonical_skills=["python", "langchain"])


def make_job(**overrides) -> Job:
    number = next(_job_counter)
    data = {
        "external_id": f"demo-{number}",
        "source": "demo",
        "fingerprint": f"fingerprint-{number}",
        "title": "AI Engineer",
        "company": "Aurora Labs",
        "location": "Bengaluru, India",
        "remote": False,
        "seniority": "mid",
        "role_family": "ai_ml",
        "salary_min": 1_200_000,
        "salary_max": 1_800_000,
        "currency": "INR",
        "description": "Build retrieval systems for enterprise search.",
        "skills": ["python", "rag"],
        "posted_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "url": "https://demo.example/jobs/ai-engineer",
    }
    data.update(overrides)
    return Job(**data)
