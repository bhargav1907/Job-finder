from app.config import get_settings
from app.services.ingest import build_job, ingest_raw
from app.sources.base import JobQuery
from app.sources.seed import SeedSource


def test_seed_corpus_has_unstated_salary_jobs():
    raw_jobs = SeedSource(get_settings().seed_path).fetch(JobQuery())
    unstated = [job for job in raw_jobs
                if job.salary_min is None or job.salary_max is None]
    assert 3 <= len(unstated) <= 5
    assert all(job.salary_min is None and job.salary_max is None for job in unstated)
    fingerprints = [build_job(job).fingerprint for job in raw_jobs]
    assert len(fingerprints) == len(set(fingerprints))


def test_seed_ingest_is_idempotent(session):
    raw_jobs = SeedSource(get_settings().seed_path).fetch(JobQuery())
    first = ingest_raw(session, raw_jobs, embed=False)
    second = ingest_raw(session, raw_jobs, embed=False)
    assert first.inserted == len(raw_jobs)
    assert second.inserted == 0
