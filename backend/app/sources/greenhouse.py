"""Greenhouse public board API. Keyless and read-only."""

import logging
from collections.abc import Sequence

import httpx

from .base import JobQuery, RawJob, SourceError
from .boards import Board
from .http import client_scope
from .mapping import html_to_text, parse_iso_datetime

logger = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseSource:
    name = "greenhouse"

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
                    logger.warning("greenhouse: board %s failed: %s", board.board, exc)
        return jobs

    def _fetch_board(self, client: httpx.Client, board: Board) -> list[RawJob]:
        response = client.get(
            f"{BASE_URL}/{board.board}/jobs",
            params={"content": "true", "pay_transparency": "true"},
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise SourceError(f"{board.board}: response has no jobs list")

        jobs: list[RawJob] = []
        for row in rows:
            if not isinstance(row, dict):
                raise SourceError(f"{board.board}: posting is not an object")
            external_id = str(row.get("id") or "").strip()
            title = str(row.get("title") or "").strip()
            if not external_id or not title:
                logger.warning("greenhouse: %s: skipping posting without id or title", board.board)
                continue

            location = row.get("location")
            location_name = location.get("name", "") if isinstance(location, dict) else ""
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=external_id,
                    title=title,
                    company=board.company,
                    location=location_name or "",
                    description=html_to_text(str(row.get("content") or "")),
                    url=str(row.get("absolute_url") or ""),
                    posted_at=parse_iso_datetime(row.get("updated_at")),
                )
            )
        return jobs
