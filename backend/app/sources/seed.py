import json
from datetime import datetime
from pathlib import Path

from .base import JobQuery, RawJob


class SeedSource:
    """Reads the committed demo corpus. Never touches the network."""

    name = "demo"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def fetch(self, query: JobQuery) -> list[RawJob]:
        if not self.path.exists():
            return []

        rows = json.loads(self.path.read_text(encoding="utf-8"))
        jobs: list[RawJob] = []
        for row in rows:
            posted = row.get("posted_at")
            jobs.append(
                RawJob(
                    source=row.get("source", "demo"),
                    external_id=str(row.get("id", "")),
                    title=row["title"],
                    company=row["company"],
                    location=row.get("location", ""),
                    description=row.get("description", ""),
                    url=row.get("url", ""),
                    remote=bool(row.get("remote", False)),
                    salary_min=row.get("salary_min"),
                    salary_max=row.get("salary_max"),
                    currency=row.get("currency", "INR"),
                    posted_at=datetime.fromisoformat(posted) if posted else None,
                )
            )
        return jobs
