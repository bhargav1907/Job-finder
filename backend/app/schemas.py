from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str
    remote: bool
    seniority: str
    role_family: str
    salary_min: int | None
    salary_max: int | None
    currency: str
    skills: list[str]
    posted_at: datetime | None
    url: str
    source: str


class JobList(BaseModel):
    items: list[JobRead]
    total: int
    limit: int
    offset: int


class IngestStats(BaseModel):
    fetched: int
    inserted: int
    skipped: int
    embedded: int


class ExperienceEntry(BaseModel):
    title: str
    company: str
    start: str = ""
    end: str = ""
    highlights: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str
    institution: str
    year: str = ""


class LLMParsedProfile(BaseModel):
    """Exactly what the model returns; every field is required."""

    name: str
    email: str
    phone: str
    location: str
    summary: str
    total_years_experience: float = Field(ge=0, le=60)
    seniority: Literal["intern", "junior", "mid", "senior", "lead"]
    target_roles: list[str]
    preferred_locations: list[str]
    remote_ok: bool
    salary_min: int | None = Field(ge=0)
    salary_max: int | None = Field(ge=0)
    currency: str
    skills: list[str]
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    certifications: list[str]
    projects: list[str]


class ResumeProfile(LLMParsedProfile):
    canonical_skills: list[str]


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    profile: ResumeProfile
    parse_model: str
    content_hash: str
    created_at: datetime


class RecommendationItem(BaseModel):
    job: JobRead
    score: float
    retrieval_score: float
    matched_skills: list[str]
    reasons: list[str]
    gaps: list[str]
    reranked: bool


class RecommendationList(BaseModel):
    resume_id: int
    items: list[RecommendationItem]
    items_without_salary: list[RecommendationItem]
    total: int
    without_salary_total: int
    limit: int
    retrieval_version: str
    rerank_status: Literal["ok", "partial", "unavailable"]
    rerank_version: str
