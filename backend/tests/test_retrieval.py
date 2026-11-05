from datetime import datetime, timezone

import numpy as np
import pytest

from app.embeddings import to_bytes
from app.models import Resume
from app.services.retrieval import (
    Candidate,
    RetrievalFilters,
    _sort_key,
    retrieve_jobs,
)
from tests.factories import make_job, make_profile


def add_resume(session, *, skills=("python",), vector=(1.0, 0.0), embedded=True):
    profile = make_profile()
    profile.canonical_skills = list(skills)
    row = Resume(
        filename="priya.txt",
        text="Priya Sharma\nPython",
        profile=profile.model_dump(),
        embedding=to_bytes(np.array(vector, dtype=np.float32)) if embedded else None,
        content_hash="resume-hash",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def add_job(session, *, vector=(1.0, 0.0), skills=("python",), **overrides):
    embedding = None if vector is None else to_bytes(np.array(vector, dtype=np.float32))
    job = make_job(embedding=embedding, skills=list(skills), **overrides)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_ranks_by_cosine_similarity(session):
    resume = add_resume(session)
    best = add_job(session, vector=(1.0, 0.0), skills=[])
    worst = add_job(session, vector=(0.0, 1.0), skills=[])
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [best.id, worst.id]
    assert result.items[0].score == 0.85
    assert result.items[1].score == 0.0


def test_skill_overlap_breaks_semantic_ties(session):
    resume = add_resume(session, skills=("python", "rag"))
    overlap = add_job(session, vector=(1.0, 0.0), skills=["python", "rag"])
    miss = add_job(session, vector=(1.0, 0.0), skills=["java"])
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [overlap.id, miss.id]
    assert result.items[0].score == 1.0
    assert result.items[1].score == 0.85


def test_negative_cosine_is_clamped_to_zero(session):
    resume = add_resume(session)
    add_job(session, vector=(-1.0, 0.0), skills=[])
    assert retrieve_jobs(session, resume).items[0].score == 0.0


def test_ties_prefer_newer_postings(session):
    resume = add_resume(session)
    older = add_job(session, posted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = add_job(session, posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc))
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [newer.id, older.id]


def test_naive_posted_at_does_not_break_sorting():
    older = make_job(posted_at=datetime(2026, 1, 1))
    newer = make_job(posted_at=datetime(2026, 2, 1))
    ordered = sorted(
        [
            Candidate(job=older, score=0.5, matched_skills=[]),
            Candidate(job=newer, score=0.5, matched_skills=[]),
        ],
        key=_sort_key,
    )
    assert [c.job.posted_at for c in ordered] == [newer.posted_at, older.posted_at]


def test_limit_caps_items_but_not_total(session):
    resume = add_resume(session)
    for _ in range(3):
        add_job(session)
    result = retrieve_jobs(session, resume, limit=2)
    assert len(result.items) == 2
    assert result.total == 3
    assert result.items_without_salary == []
    assert result.without_salary_total == 0


def test_jobs_without_embeddings_or_with_wrong_dimensions_are_skipped(session):
    resume = add_resume(session)
    kept = add_job(session)
    add_job(session, vector=None)
    add_job(session, vector=(1.0, 0.0, 0.0))
    result = retrieve_jobs(session, resume)
    assert [c.job.id for c in result.items] == [kept.id]
    assert result.total == 1


def test_resume_without_embedding_is_embedded_and_saved(session, monkeypatch):
    resume = add_resume(session, embedded=False)
    job = add_job(session, skills=[])
    monkeypatch.setattr(
        "app.services.retrieval.embed_texts",
        lambda texts: np.array([[1.0, 0.0]], dtype=np.float32),
    )
    result = retrieve_jobs(session, resume)
    assert result.items[0].job.id == job.id
    session.refresh(resume)
    assert resume.embedding is not None


def test_location_is_a_case_insensitive_substring(session):
    resume = add_resume(session)
    match = add_job(session, location="Bengaluru, India")
    add_job(session, location="Chennai, India")
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(location="bengaluru"))
    assert [c.job.id for c in result.items] == [match.id]


def test_location_remote_matches_jobs_flagged_remote(session):
    resume = add_resume(session)
    remote_flag = add_job(session, location="Chennai, India", remote=True)
    remote_text = add_job(session, location="Remote, India", remote=False)
    add_job(session, location="Pune, India", remote=False)
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(location="remote"))
    assert {c.job.id for c in result.items} == {remote_flag.id, remote_text.id}


def test_remote_filter_is_exact(session):
    resume = add_resume(session)
    remote = add_job(session, remote=True)
    add_job(session, remote=False)
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(remote=True))
    assert [c.job.id for c in result.items] == [remote.id]


@pytest.mark.parametrize(
    "years,expected",
    [
        (0, {"intern", "junior"}),
        (1, {"junior", "mid"}),
        (2, {"junior", "mid"}),
        (3, {"mid", "senior"}),
        (5, {"mid", "senior"}),
        (6, {"senior", "lead"}),
    ],
)
def test_experience_maps_to_two_seniority_tiers(session, years, expected):
    resume = add_resume(session)
    for level in ("intern", "junior", "mid", "senior", "lead"):
        add_job(session, seniority=level)
    result = retrieve_jobs(
        session, resume, filters=RetrievalFilters(experience_years=years)
    )
    assert {c.job.seniority for c in result.items} == expected


def test_role_filter_uses_inferred_family(session):
    resume = add_resume(session)
    ai = add_job(session, title="AI Engineer", role_family="ai_ml")
    add_job(session, title="Data Scientist", role_family="data")
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(role="AI Engineer"))
    assert [c.job.id for c in result.items] == [ai.id]


def test_unmapped_role_falls_back_to_title_substring(session):
    resume = add_resume(session)
    widget = add_job(session, title="Widget Wrangler", role_family="other")
    add_job(session, title="Data Scientist", role_family="data")
    result = retrieve_jobs(session, resume, filters=RetrievalFilters(role="Widget"))
    assert [c.job.id for c in result.items] == [widget.id]


def test_like_wildcards_are_escaped(session):
    resume = add_resume(session)
    add_job(session, location="Bengaluru, India")
    add_job(session, location="Chennai, India")
    assert retrieve_jobs(
        session, resume, filters=RetrievalFilters(location="%")
    ).items == []
    assert retrieve_jobs(
        session, resume, filters=RetrievalFilters(role="_")
    ).items == []
