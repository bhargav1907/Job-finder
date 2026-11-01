from datetime import datetime, timezone

from sqlalchemy import JSON, Column, LargeBinary, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(default="", index=True)
    source: str = Field(default="demo", index=True)
    fingerprint: str = Field(index=True, unique=True)

    title: str = Field(index=True)
    company: str = Field(index=True)
    location: str = Field(default="", index=True)
    remote: bool = Field(default=False)
    seniority: str = Field(default="", index=True)
    role_family: str = Field(default="", index=True)

    salary_min: int | None = None
    salary_max: int | None = None
    currency: str = "INR"

    description: str = Field(default="", sa_column=Column(Text))
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    posted_at: datetime | None = None
    url: str = ""

    embedding: bytes | None = Field(default=None, sa_column=Column(LargeBinary))
    extracted_at: datetime | None = None
    extraction_model: str = "heuristic-v1"


class Resume(SQLModel, table=True):
    __tablename__ = "resumes"

    id: int | None = Field(default=None, primary_key=True)
    filename: str = ""
    text: str = Field(default="", sa_column=Column(Text))
    profile: dict = Field(default_factory=dict, sa_column=Column(JSON))
    embedding: bytes | None = Field(default=None, sa_column=Column(LargeBinary))
    content_hash: str = Field(default="", index=True)
    parse_model: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class Match(SQLModel, table=True):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("resume_id", "job_id", "prompt_version"),)

    id: int | None = Field(default=None, primary_key=True)
    resume_id: int = Field(foreign_key="resumes.id", index=True)
    job_id: int = Field(foreign_key="jobs.id", index=True)
    score: int
    reasons: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    gaps: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    model: str = ""
    prompt_version: str = "v1"
    created_at: datetime = Field(default_factory=utcnow)
