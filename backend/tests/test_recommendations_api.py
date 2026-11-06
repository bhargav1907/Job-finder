import re

import numpy as np
import pytest

from app.config import get_settings
from app.embeddings import to_bytes
from app.models import Resume
from app.services.rerank import prompt_version
from tests.factories import make_job, make_profile


@pytest.fixture(autouse=True)
def fake_rerank_client(monkeypatch):
    class FakeRerankClient:
        def complete_json(self, system, user, *, model, max_tokens=1024,
                          json_schema=None, purpose=""):
            ids = [int(value) for value in re.findall(r"JOB (\d+)", user)]
            return {"results": [
                {"job_id": job_id, "score": 80,
                 "reasons": ["Matches the target role."],
                 "gaps": ["Add production testing depth."]}
                for job_id in ids
            ]}

    monkeypatch.setattr("app.services.rerank.LLMClient", FakeRerankClient)


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
    assert body["rerank_status"] == "ok"
    assert body["rerank_version"] == prompt_version(get_settings().llm_rerank_model)
    assert body["limit"] == 30
    assert body["total"] == 2
    assert body["without_salary_total"] == 0
    assert body["items_without_salary"] == []
    assert {item["job"]["id"] for item in body["items"]} == {job.id for job in jobs}
    item = body["items"][0]
    assert item["matched_skills"] == ["python"]
    assert item["reasons"] == ["Matches the target role."]
    assert item["gaps"] == ["Add production testing depth."]
    assert item["reranked"] is True
    assert item["retrieval_score"] == 1.0
    assert "text" not in item["job"]


def test_missing_resume_returns_404(api):
    assert api.get("/api/resumes/9999/recommendations").status_code == 404


def test_limit_is_respected(api, session):
    resume, _ = seed(session, job_count=3)
    body = api.get(f"/api/resumes/{resume.id}/recommendations?limit=1").json()
    assert len(body["items"]) == 1
    assert body["total"] == 3


def test_default_limit_is_final_top_k(api, session):
    resume, _ = seed(session, job_count=41)
    body = api.get(f"/api/resumes/{resume.id}/recommendations").json()
    assert len(body["items"]) == 30
    assert body["total"] == 40


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


def test_unstated_jobs_are_visible_without_a_salary_filter(api, session):
    resume, _ = seed(session, job_count=1)
    unknown = make_job(
        title="No Salary Role",
        salary_min=None,
        salary_max=None,
        embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
    )
    session.add(unknown)
    session.commit()
    body = api.get(f"/api/resumes/{resume.id}/recommendations").json()
    assert len(body["items"]) == 1
    assert [item["job"]["id"] for item in body["items_without_salary"]] == [unknown.id]


def test_unstated_backfills_when_known_is_short(api, session):
    resume = seed(session, job_count=1)[0]
    for index in range(12):
        session.add(make_job(
            title=f"Unstated {index}",
            salary_min=None,
            salary_max=None,
            embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
        ))
    session.commit()
    body = api.get(f"/api/resumes/{resume.id}/recommendations").json()
    assert len(body["items"]) == 1
    assert len(body["items_without_salary"]) == 12


def test_rerank_fields_are_present(api, session):
    resume, _ = seed(session, job_count=1)
    body = api.get(f"/api/resumes/{resume.id}/recommendations").json()
    item = body["items"][0]
    assert isinstance(item["retrieval_score"], float)
    assert isinstance(item["score"], float)
    assert isinstance(item["reasons"], list)
    assert isinstance(item["gaps"], list)
    assert isinstance(item["reranked"], bool)
    assert body["rerank_status"] in {"ok", "partial", "unavailable"}
    assert isinstance(body["rerank_version"], str)


@pytest.mark.parametrize(
    "query",
    ["experience_years=-1", "salary_min=-1", "limit=0", "limit=101"],
)
def test_invalid_query_values_return_422(api, query):
    assert api.get(f"/api/resumes/1/recommendations?{query}").status_code == 422
