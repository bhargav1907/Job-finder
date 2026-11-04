from app.schemas import ResumeProfile

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
