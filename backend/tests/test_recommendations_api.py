import numpy as np
import pytest

from app.embeddings import to_bytes
from app.models import Resume
from tests.factories import make_job, make_profile


def seed(session, *, job_count=2):
    profile = make_profile()
    resume = Resume(
        filename="priya.txt",
        text="Priya Sharma\nPython",
        profile=profile.model_dump(),
        embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
        content_hash="api-resume-hash",
    )
    session.add(resume)
    session.commit()
    session.refresh(resume)

    jobs = []
    for index in range(job_count):
        job = make_job(
            title=f"AI Engineer {index}",
            embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
            skills=["python"],
        )
        session.add(job)
        jobs.append(job)
    session.commit()
    for job in jobs:
        session.refresh(job)
    return resume, jobs


def test_returns_ranked_recommendations(api, session):
    resume, jobs = seed(session)
    response = api.get(f"/api/resumes/{resume.id}/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume.id
    assert body["retrieval_version"] == "v1"
    assert body["limit"] == 40
    assert body["total"] == 2
    assert body["without_salary_total"] == 0
    assert body["items_without_salary"] == []
    assert {item["job"]["id"] for item in body["items"]} == {job.id for job in jobs}
    assert body["items"][0]["matched_skills"] == ["python"]
    assert "text" not in body["items"][0]["job"]


def test_missing_resume_returns_404(api):
    assert api.get("/api/resumes/9999/recommendations").status_code == 404


def test_limit_is_respected(api, session):
    resume, _ = seed(session, job_count=3)
    body = api.get(f"/api/resumes/{resume.id}/recommendations?limit=1").json()
    assert len(body["items"]) == 1
    assert body["total"] == 3


def test_default_limit_is_the_configured_top_k(api, session):
    resume, _ = seed(session, job_count=41)
    body = api.get(f"/api/resumes/{resume.id}/recommendations").json()
    assert len(body["items"]) == 40
    assert body["total"] == 41


def test_filters_are_passed_through(api, session):
    resume, jobs = seed(session)
    jobs[0].location = "Bengaluru, India"
    jobs[1].location = "Chennai, India"
    session.add(jobs[0])
    session.add(jobs[1])
    session.commit()
    body = api.get(
        f"/api/resumes/{resume.id}/recommendations?location=Bengaluru"
    ).json()
    assert [item["job"]["id"] for item in body["items"]] == [jobs[0].id]


def test_salary_split_is_exposed(api, session):
    resume, _ = seed(session, job_count=1)
    unknown = make_job(
        title="No Salary Role",
        salary_min=None,
        salary_max=None,
        embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
    )
    session.add(unknown)
    session.commit()
    body = api.get(
        f"/api/resumes/{resume.id}/recommendations?salary_min=1500000"
    ).json()
    assert len(body["items"]) == 1
    assert [item["job"]["id"] for item in body["items_without_salary"]] == [unknown.id]


@pytest.mark.parametrize(
    "query",
    ["experience_years=-1", "salary_min=-1", "limit=0", "limit=101"],
)
def test_invalid_query_values_return_422(api, query):
    assert api.get(f"/api/resumes/1/recommendations?{query}").status_code == 422
