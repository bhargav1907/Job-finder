import numpy as np

from app.embeddings import to_bytes
from app.models import Resume
from app.services.recommend import blend_score, recommend_jobs
from app.services.rerank import RerankOutcome, RerankResult
from app.services.retrieval import Candidate, RetrievalResult
from tests.factories import make_job, make_profile


def add_resume(session):
    profile = make_profile()
    resume = Resume(filename="priya.txt", text="Priya", profile=profile.model_dump(),
                    embedding=to_bytes(np.array([1.0, 0.0], dtype=np.float32)),
                    content_hash="recommend-resume")
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


def add_job(session, **overrides):
    job = make_job(**overrides)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def add_jobs(session, count, **overrides):
    title = overrides.pop("title", "Job")
    return [add_job(session, title=f"{title} {index}", **overrides)
            for index in range(count)]


def candidate(job, score):
    return Candidate(job=job, score=score, matched_skills=[])


def retrieval(paid, unknown=()):
    return RetrievalResult(items=list(paid), items_without_salary=list(unknown),
                           total=len(paid), without_salary_total=len(unknown))


def rerank_all(jobs, score=80, reranked=True):
    return RerankOutcome(
        results={job.id: RerankResult(score=score, reasons=["fits"], gaps=["gap"],
                                      reranked=reranked) for job in jobs},
        status="ok" if reranked else "unavailable",
    )


def test_blend_is_seventy_thirty():
    assert blend_score(80, 0.5, 0.7) == 71.0


def test_blend_endpoints():
    assert blend_score(100, 0.0, 0.7) == 70.0
    assert blend_score(0, 1.0, 0.7) == 30.0


def test_ordering_uses_blended_score(session, monkeypatch):
    resume = add_resume(session)
    low_llm = add_job(session, title="Low", embedding=None)
    high_llm = add_job(session, title="High", embedding=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(low_llm, 0.9),
                                                   candidate(high_llm, 0.4)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(results={
                            low_llm.id: RerankResult(60, ["a"], ["b"], True),
                            high_llm.id: RerankResult(90, ["a"], ["b"], True),
                        }, status="ok"))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == [high_llm.id, low_llm.id]


def test_equal_blends_fall_back_to_retrieval_score(session, monkeypatch):
    resume = add_resume(session)
    lower = add_job(session, title="Lower retrieval", embedding=None)
    higher = add_job(session, title="Higher retrieval", embedding=None)
    monkeypatch.setattr("app.services.recommend.blend_score", lambda *a, **k: 50.0)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(lower, 0.4),
                                                   candidate(higher, 0.7)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(results={
                            lower.id: RerankResult(80, ["a"], ["b"], True),
                            higher.id: RerankResult(70, ["a"], ["b"], True),
                        }, status="ok"))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == [higher.id, lower.id]


def test_equal_everything_falls_back_to_job_id(session, monkeypatch):
    resume = add_resume(session)
    first = add_job(session, title="First", embedding=None)
    second = add_job(session, title="Second", embedding=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(second, 0.5),
                                                   candidate(first, 0.5)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(results={
                            first.id: RerankResult(80, ["a"], ["b"], True),
                            second.id: RerankResult(80, ["a"], ["b"], True),
                        }, status="ok"))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == sorted([first.id, second.id])


def seed_partition(session, known, unstated):
    resume = add_resume(session)
    known_jobs = add_jobs(session, known, title="Known")
    unstated_jobs = add_jobs(session, unstated, title="Unstated",
                             salary_min=None, salary_max=None)
    paid = [candidate(job, 0.5) for job in known_jobs]
    unknown = [candidate(job, 0.5) for job in unstated_jobs]
    return resume, known_jobs, unstated_jobs, paid, unknown


def test_default_split_is_twenty_known_ten_unstated(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 25, 15)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume)
    assert (len(result.items), len(result.items_without_salary)) == (20, 10)


def test_unstated_is_short_known_backfills(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 30, 3)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume)
    assert (len(result.items), len(result.items_without_salary)) == (27, 3)


def test_known_is_short_unstated_backfills(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 15, 25)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume)
    assert (len(result.items), len(result.items_without_salary)) == (15, 15)


def test_limit_scales_the_target(session, monkeypatch):
    resume, _, _, paid, unknown = seed_partition(session, 25, 15)
    jobs = [c.job for c in paid + unknown]
    monkeypatch.setattr("app.services.recommend.retrieve_jobs", lambda *a, **k: retrieval(paid, unknown))
    monkeypatch.setattr("app.services.recommend.rerank_jobs", lambda *a, **k: rerank_all(jobs))
    result = recommend_jobs(session, resume, limit=6)
    assert (len(result.items), len(result.items_without_salary)) == (4, 2)


def test_degraded_item_uses_retrieval_score_and_empty_explanations(session, monkeypatch):
    resume = add_resume(session)
    job = add_job(session, embedding=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(job, 0.5)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: RerankOutcome(
                            results={job.id: RerankResult(0, [], [], False)},
                            status="unavailable"))
    item = recommend_jobs(session, resume).items[0]
    assert item.score == 50.0
    assert item.reasons == [] and item.gaps == []
    assert item.reranked is False


def test_unstated_jobs_move_out_of_items_without_a_salary_filter(session, monkeypatch):
    resume = add_resume(session)
    known = add_job(session, embedding=None)
    unknown = add_job(session, embedding=None, salary_min=None, salary_max=None)
    monkeypatch.setattr("app.services.recommend.retrieve_jobs",
                        lambda *a, **k: retrieval([candidate(known, 0.5),
                                                   candidate(unknown, 0.5)]))
    monkeypatch.setattr("app.services.recommend.rerank_jobs",
                        lambda *a, **k: rerank_all([known, unknown]))
    result = recommend_jobs(session, resume)
    assert [item.job.id for item in result.items] == [known.id]
    assert [item.job.id for item in result.items_without_salary] == [unknown.id]
    assert (result.total, result.without_salary_total) == (1, 1)
