"""python -m app.cli ingest"""

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from sqlmodel import Session

from .config import get_settings
from .db import engine, init_db
from .services.ingest import ingest_raw
from .services.resumes import reembed_resumes
from .sources.base import JobQuery, JobSource, RawJob
from .sources.boards import load_boards
from .sources.registry import build_sources
from .sources.seed import SeedSource

logger = logging.getLogger(__name__)


def fetch_live(sources: Sequence[JobSource]) -> list[RawJob]:
    """Collect every configured board, but fail loudly if all of them came back empty."""
    raw_jobs: list[RawJob] = []
    for source in sources:
        fetched = source.fetch(JobQuery())
        if not fetched:
            logger.warning("cli: %s returned no postings", source.name)
        raw_jobs.extend(fetched)
    if not raw_jobs:
        raise SystemExit("no live postings fetched; check board availability")
    return raw_jobs


def cmd_ingest(args: argparse.Namespace) -> None:
    init_db()
    settings = get_settings()
    if args.live:
        raw_jobs = fetch_live(build_sources(load_boards(args.boards or settings.boards_path)))
    else:
        raw_jobs = SeedSource(settings.seed_path).fetch(JobQuery())
    with Session(engine) as session:
        result = ingest_raw(session, raw_jobs, embed=not args.no_embed)
    print(json.dumps(result.as_dict(), indent=2))


def cmd_reembed(args: argparse.Namespace) -> None:
    init_db()
    with Session(engine) as session:
        count = reembed_resumes(session)
    print(json.dumps({"reembedded": count}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Load the seed corpus or live ATS boards")
    ingest.add_argument("--no-embed", action="store_true", help="Skip embedding")
    ingest.add_argument(
        "--live", action="store_true", help="Fetch live ATS boards instead of seed jobs"
    )
    ingest.add_argument(
        "--boards", type=Path, default=None, help="Board catalogue (defaults to data/boards.json)"
    )
    ingest.set_defaults(func=cmd_ingest)

    reembed = subparsers.add_parser("reembed", help="Recompute stored resume embeddings")
    reembed.set_defaults(func=cmd_reembed)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
