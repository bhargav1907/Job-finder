from app.services.rerank import _job_card, _resume_card, prompt_version
from tests.factories import make_job, make_profile


def test_prompt_version_includes_model():
    assert prompt_version("lfm3:1.7b") == "rerank-v1@lfm3:1.7b"


def test_job_card_is_compact_and_marks_salary():
    job = make_job(id=7, description="y" * 600)
    card = _job_card(job)
    assert card.startswith("JOB 7")
    assert "y" * 400 in card
    assert "y" * 401 not in card
    assert "Salary: 1200000-1800000 INR" in card


def test_job_card_marks_missing_salary():
    job = make_job(id=8, salary_min=None, salary_max=None)
    assert "Salary: not stated" in _job_card(job)


def test_resume_card_is_bounded():
    card = _resume_card(make_profile())
    assert len(card) <= 800
    assert "1.5 years" in card
    assert "python" in card


import re

import httpx
import numpy as np

from app.embeddings import to_bytes
from app.models import Resume
from app.services.rerank import RerankOutcome, rerank_jobs


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete_json(self, system, user, *, model, max_tokens=1024,
                      json_schema=None, purpose=""):
        self.calls.append(user)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def add_resume(session):
    profile = make_profile()
    resume = Resume(filename="priya.txt", text="Priya", profile=profile.model_dump(),
                    embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
                    content_hash="rerank-resume")
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


def add_jobs(session, count, **overrides):
    jobs = []
    for index in range(count):
        job = make_job(title=f"AI Engineer {index}", **overrides)
        session.add(job)
        jobs.append(job)
    session.commit()
    for job in jobs:
        session.refresh(job)
    return jobs


def valid_response(ids):
    return {"results": [
        {"job_id": job_id, "score": 80, "reasons": ["Fits the role."],
         "gaps": ["Add testing depth."]}
        for job_id in ids
    ]}


def batch_ids(prompt):
    return sorted(int(value) for value in re.findall(r"JOB (\d+)", prompt))


def test_batches_ten_jobs_and_covers_every_id(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 23)
    client = FakeClient(*(
        valid_response([job.id for job in jobs[start:start + 10]])
        for start in range(0, 23, 10)
    ))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert [len(batch_ids(call)) for call in client.calls] == [10, 10, 3]
    assert set(outcome.results) == {job.id for job in jobs}
    assert all(result.reranked for result in outcome.results.values())
    assert outcome.status == "ok"


def test_missing_id_retries_once_then_succeeds(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 2)
    ids = [job.id for job in jobs]
    client = FakeClient(valid_response(ids[:1]), valid_response(ids))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 2
    assert set(outcome.results) == set(ids)
    assert outcome.status == "ok"


def test_duplicate_or_unknown_id_rejects_and_degrades_after_retry(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 2)
    ids = [job.id for job in jobs]
    bad = {"results": [
        {"job_id": ids[0], "score": 80, "reasons": ["a"], "gaps": ["b"]},
        {"job_id": ids[0], "score": 90, "reasons": ["a"], "gaps": ["b"]},
    ]}
    client = FakeClient(bad, bad)
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 2
    assert all(not result.reranked for result in outcome.results.values())
    assert outcome.status == "unavailable"


def test_string_score_rejects_batch(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    bad = {"results": [{"job_id": jobs[0].id, "score": "82",
                        "reasons": ["a"], "gaps": ["b"]}]}
    client = FakeClient(bad, bad)
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert outcome.results[jobs[0].id].reranked is False


def test_empty_reasons_rejects_batch(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    bad = {"results": [{"job_id": jobs[0].id, "score": 82,
                        "reasons": [], "gaps": ["b"]}]}
    client = FakeClient(bad, bad)
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert outcome.results[jobs[0].id].reranked is False


def test_long_lists_are_truncated_to_three(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 1)
    response = {"results": [{
        "job_id": jobs[0].id, "score": 82,
        "reasons": ["r1", "r2", "r3", "r4", "r5"],
        "gaps": ["g1", "g2", "g3", "g4"],
    }]}
    outcome = rerank_jobs(session, resume, jobs, client=FakeClient(response))
    result = outcome.results[jobs[0].id]
    assert result.reranked is True
    assert result.reasons == ["r1", "r2", "r3"]
    assert result.gaps == ["g1", "g2", "g3"]


def test_http_error_degrades_all_and_stops_calling(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 12)
    client = FakeClient(httpx.ConnectError("down"))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert len(client.calls) == 1
    assert len(outcome.results) == 12
    assert outcome.status == "unavailable"


def test_partial_status_when_one_batch_fails(session):
    resume = add_resume(session)
    jobs = add_jobs(session, 12)
    ids = [job.id for job in jobs]
    client = FakeClient(valid_response(ids[:10]), httpx.ConnectError("down"))
    outcome = rerank_jobs(session, resume, jobs, client=client)
    assert outcome.status == "partial"
    assert sum(result.reranked for result in outcome.results.values()) == 10


def test_empty_job_list_is_ok(session):
    resume = add_resume(session)
    client = FakeClient()
    outcome = rerank_jobs(session, resume, [], client=client)
    assert outcome.results == {}
    assert outcome.status == "ok"
    assert client.calls == []
