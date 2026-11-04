"""Orchestrate resume extraction, parsing, embedding, and storage."""

import hashlib

from sqlmodel import Session, select

from ..config import get_settings
from ..embeddings import embed_texts, to_bytes
from ..llm.client import LLMClient
from ..models import Resume
from ..schemas import ResumeProfile
from .resume_parse import parse_resume_text
from .resume_text import extract_text


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_resume(
    session: Session,
    filename: str,
    data: bytes,
    *,
    client: LLMClient | None = None,
) -> tuple[Resume, bool]:
    """Store a parsed resume. Returns (row, created); duplicates skip the model."""
    settings = get_settings()
    text = extract_text(filename, data, max_chars=settings.resume_max_chars)
    digest = content_hash(text)

    existing = session.exec(select(Resume).where(Resume.content_hash == digest)).first()
    if existing:
        return existing, False

    profile, parse_model = parse_resume_text(text, client=client)
    vector = embed_texts([_embed_text(profile)])[0]
    row = Resume(
        filename=filename,
        text=text,
        profile=profile.model_dump(),
        embedding=to_bytes(vector),
        content_hash=digest,
        parse_model=parse_model,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row, True


def _embed_text(profile: ResumeProfile) -> str:
    roles = ", ".join(profile.target_roles)
    skills = ", ".join(profile.skills)
    experience = "; ".join(f"{item.title} at {item.company}" for item in profile.experience)
    education = "; ".join(f"{item.degree} at {item.institution}" for item in profile.education)
    projects = "; ".join(profile.projects)
    return (
        f"{profile.summary}. Roles: {roles}. Skills: {skills}. "
        f"Experience: {experience}. Education: {education}. Projects: {projects}"
    )
