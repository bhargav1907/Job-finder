"""Keka career portals. Keyless and read-only."""

import logging
from collections.abc import Sequence

import httpx

from .base import JobQuery, RawJob, SourceError
from .boards import Board
from .http import client_scope
from .mapping import html_to_text, join_nonempty, parse_iso_datetime

logger = logging.getLogger(__name__)


class KekaSource:
    name = "keka"

    def __init__(self, boards: Sequence[Board], client: httpx.Client | None = None):
        self.boards = tuple(boards)
        self._client = client

    def fetch(self, query: JobQuery) -> list[RawJob]:
        jobs: list[RawJob] = []
        with client_scope(self._client) as client:
            for board in self.boards:
                try:
                    jobs.extend(self._fetch_board(client, board))
                except (httpx.HTTPError, KeyError, SourceError, ValueError) as exc:
                    logger.warning("keka: board %s failed: %s", board.board, exc)
        return jobs

    def _fetch_board(self, client: httpx.Client, board: Board) -> list[RawJob]:
        base = f"https://{board.board}.keka.com/careers"
        response = client.get(f"{base}/api/jobs/default/active")
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise SourceError(f"{board.board}: response is not a job list")

        jobs: list[RawJob] = []
        for row in rows:
            if not isinstance(row, dict):
                raise SourceError(f"{board.board}: posting is not an object")
            external_id = str(row.get("id") or "").strip()
            title = str(row.get("title") or "").strip()
            if not external_id or not title:
                logger.warning("keka: %s: skipping posting without id or title", board.board)
                continue

            location = ""
            locations = row.get("jobLocations")
            if isinstance(locations, list) and locations and isinstance(locations[0], dict):
                first = locations[0]
                location = join_nonempty(
                    str(first.get("city") or ""),
                    str(first.get("state") or ""),
                    str(first.get("countryName") or ""),
                )

            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=external_id,
                    title=title,
                    company=board.company,
                    location=location,
                    description=html_to_text(str(row.get("description") or "")),
                    url=f"{base}/jobdetails/{external_id}",
                    remote="remote" in location.lower() or "remote" in title.lower(),
                    posted_at=parse_iso_datetime(row.get("publishedOn")),
                )
            )
        return jobs
