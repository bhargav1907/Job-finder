"""Darwinbox career portals. Keyless and read-only."""

import logging
import re
from collections.abc import Sequence

import httpx

from ..services.normalize import normalize_ws
from .base import JobQuery, RawJob, SourceError
from .boards import Board
from .http import client_scope
from .mapping import html_to_text, parse_epoch_seconds

logger = logging.getLogger(__name__)

_HOST_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*\.darwinbox\.(?:in|com)$")
_DOUBLE_ENCODED = re.compile(r"&amp;lt;/?[a-zA-Z]", re.IGNORECASE)
_ONCE_ENCODED = re.compile(r"&lt;/?[a-zA-Z]", re.IGNORECASE)
_PAGE_SIZE = 100
_MAX_PAGES = 50


class DarwinboxSource:
    name = "darwinbox"

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
                    logger.warning("darwinbox: board %s failed: %s", board.board, exc)
        return jobs

    def _fetch_board(self, client: httpx.Client, board: Board) -> list[RawJob]:
        if not _HOST_PATTERN.fullmatch(board.board):
            raise SourceError(f"{board.board}: not a Darwinbox tenant host")
        base = f"https://{board.board}"
        jobs: list[RawJob] = []
        seen: set[str] = set()
        total: int | None = None

        for page in range(1, _MAX_PAGES + 1):
            response = client.post(
                f"{base}/ms/candidateapi/job/alljobs",
                json={"page": page, "limit": _PAGE_SIZE},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("status") != "success":
                raise SourceError(f"{board.board}: page {page}: unexpected status")
            page_total = payload.get("job_counts")
            if not isinstance(page_total, int):
                raise SourceError(f"{board.board}: page {page}: job_counts is not an integer")
            if total is None:
                total = page_total

            rows = payload.get("data")
            if not isinstance(rows, list):
                raise SourceError(f"{board.board}: page {page}: data is not a list")
            if not rows:
                break

            for row in rows:
                if not isinstance(row, dict):
                    raise SourceError(f"{board.board}: page {page}: posting is not an object")
                raw_id = str(row.get("id") or "").strip()
                title = str(row.get("title") or "").strip()
                if not raw_id or not title:
                    logger.warning(
                        "darwinbox: %s: skipping posting without id or title", board.board
                    )
                    continue
                if raw_id in seen:
                    continue
                seen.add(raw_id)

                locations = row.get("officelocations_without_area")
                location = ""
                if isinstance(locations, list) and locations:
                    location = normalize_ws(str(locations[0]).replace("\r", ""))

                description = str(row.get("jd") or "")
                jobs.append(
                    RawJob(
                        source=self.name,
                        external_id=f"{board.board}:{raw_id}",
                        title=title,
                        company=board.company,
                        location=location,
                        description=_clean_description(description),
                        url=f"{base}/ms/candidatev2/main/careers/jobDetails/{raw_id}",
                        remote=(
                            row.get("is_remote") == 1
                            or "remote" in location.lower()
                            or "remote" in title.lower()
                        ),
                        posted_at=parse_epoch_seconds(row.get("posted_on")),
                    )
                )
        else:
            raise SourceError(f"{board.board}: no empty page within {_MAX_PAGES} pages")

        # An empty page is the walk's authoritative end. job_counts can drift while
        # we page, and unusable rows are skipped on purpose, so a mismatch is a
        # warning rather than grounds to discard a whole board's valid postings.
        if len(jobs) != total:
            logger.warning(
                "darwinbox: %s: gathered %d postings, board declares %d",
                board.board,
                len(jobs),
                total,
            )
        return jobs


def _clean_description(value: str) -> str:
    """Most bodies are entity-encoded once; a few are encoded twice."""
    double = len(_DOUBLE_ENCODED.findall(value))
    once = len(_ONCE_ENCODED.findall(value))
    return html_to_text(value, unescape_times=2 if double > once else 1)
