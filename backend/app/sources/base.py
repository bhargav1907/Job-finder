from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class JobQuery:
    """What the caller wants. Providers may ignore fields they cannot support."""

    keywords: str | None = None
    location: str | None = None
    remote_only: bool = False
    salary_min: int | None = None
    posted_within_days: int | None = None


@dataclass(slots=True)
class RawJob:
    """Provider-neutral listing. Normalization happens in services/ingest.py."""

    source: str
    external_id: str
    title: str
    company: str
    location: str = ""
    description: str = ""
    url: str = ""
    remote: bool = False
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str = "INR"
    posted_at: datetime | None = None


class JobSource(Protocol):
    """Every provider implements this. Routers and services never import a provider."""

    name: str

    def fetch(self, query: JobQuery) -> list[RawJob]: ...
