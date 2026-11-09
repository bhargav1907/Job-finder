"""Build live sources from the committed board catalogue."""

from collections.abc import Sequence

from .base import JobSource
from .boards import Board
from .darwinbox import DarwinboxSource
from .greenhouse import GreenhouseSource
from .keka import KekaSource

_SOURCE_TYPES = {
    "greenhouse": GreenhouseSource,
    "keka": KekaSource,
    "darwinbox": DarwinboxSource,
}


def build_sources(boards: Sequence[Board]) -> list[JobSource]:
    """One adapter per provider, in a stable order."""
    sources: list[JobSource] = []
    for provider, source_type in _SOURCE_TYPES.items():
        selected = [board for board in boards if board.provider == provider]
        if selected:
            sources.append(source_type(selected))
    return sources
