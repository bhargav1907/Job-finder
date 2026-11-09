"""The committed list of public ATS boards we are allowed to crawl."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

_BOARD_PATTERNS = {
    "greenhouse": re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$"),
    "keka": re.compile(r"^[a-z0-9][a-z0-9-]*$"),
    "darwinbox": re.compile(r"^[a-z0-9][a-z0-9-]*\.darwinbox\.(?:in|com)$"),
}


class BoardConfigError(ValueError):
    """The committed board catalogue is malformed."""


@dataclass(frozen=True, slots=True)
class Board:
    provider: str
    board: str
    company: str


def load_boards(path: str | Path) -> list[Board]:
    """Read and validate `data/boards.json`. Fail loudly; never guess a host."""
    path = Path(path)
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BoardConfigError(f"board file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BoardConfigError(f"board file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(rows, list):
        raise BoardConfigError("board file must be a JSON list")

    boards: list[Board] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise BoardConfigError(f"row {index}: expected an object")

        values = {}
        for field in ("provider", "board", "company"):
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise BoardConfigError(f"row {index}: {field} must be a non-empty string")
            values[field] = value.strip()

        provider = values["provider"]
        board = values["board"]
        company = values["company"]

        pattern = _BOARD_PATTERNS.get(provider)
        if pattern is None:
            raise BoardConfigError(f"row {index}: unknown provider {provider!r}")
        if not pattern.fullmatch(board):
            if provider == "darwinbox":
                raise BoardConfigError(
                    f"row {index}: darwinbox host must be <tenant>.darwinbox.in or "
                    f".com, got {board!r}"
                )
            raise BoardConfigError(f"row {index}: invalid {provider} board {board!r}")

        key = (provider, board)
        if key in seen:
            raise BoardConfigError(f"row {index}: duplicate board {provider}/{board}")
        seen.add(key)
        boards.append(Board(provider=provider, board=board, company=company))

    return boards
