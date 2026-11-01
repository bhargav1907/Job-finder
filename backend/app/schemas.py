from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
