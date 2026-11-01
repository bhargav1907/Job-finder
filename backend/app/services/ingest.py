from dataclasses import asdict, dataclass

from sqlmodel import Session, select

from ..embeddings import embed_texts, to_bytes
from ..models import Job, utcnow
from ..sources.base import RawJob
from .normalize import detect_seniority, extract_skills, fingerprint, infer_role_family


@dataclass
class IngestResult:
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    embedded: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def build_job(raw: RawJob) -> Job:
    text = f"{raw.title}\n{raw.description}"
    return Job(
        external_id=raw.external_id,
        source=raw.source,
        fingerprint=fingerprint(raw.title, raw.company, raw.location, raw.url),
        title=raw.title.strip(),
        company=raw.company.strip(),
        location=raw.location.strip(),
        remote=raw.remote or "remote" in (raw.location or "").lower(),
        seniority=detect_seniority(raw.title),
        role_family=infer_role_family(raw.title, raw.description),
        salary_min=raw.salary_min,
        salary_max=raw.salary_max,
        currency=raw.currency,
        description=raw.description,
        skills=extract_skills(text),
        posted_at=raw.posted_at,
        url=raw.url,
        extracted_at=utcnow(),
        extraction_model="heuristic-v1",
    )


def ingest_raw(session: Session, raw_jobs: list[RawJob], embed: bool = True) -> IngestResult:
    """Insert unseen jobs. Idempotent: re-running the same feed inserts nothing."""
    result = IngestResult(fetched=len(raw_jobs))
    seen: set[str] = set()

    for raw in raw_jobs:
        job = build_job(raw)
        if job.fingerprint in seen:
            result.skipped += 1
            continue
        seen.add(job.fingerprint)

        existing = session.exec(select(Job).where(Job.fingerprint == job.fingerprint)).first()
        if existing:
            result.skipped += 1
            continue

        session.add(job)
        result.inserted += 1

    session.commit()

    if embed:
        result.embedded = embed_missing(session)

    return result


def embed_missing(session: Session, batch_size: int = 32) -> int:
    """Embed only jobs that have no vector yet. Safe to call after every ingest."""
    pending = session.exec(select(Job).where(Job.embedding.is_(None))).all()
    if not pending:
        return 0

    embedded = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        vectors = embed_texts([_embed_text(job) for job in batch])
        for job, vector in zip(batch, vectors, strict=True):
            job.embedding = to_bytes(vector)
            session.add(job)
        session.commit()
        embedded += len(batch)
    return embedded


def _embed_text(job: Job) -> str:
    skills = ", ".join(job.skills)
    return f"{job.title} at {job.company}. {job.location}. Skills: {skills}. {job.description}"
