"""python -m app.cli ingest"""

import argparse
import json
from pathlib import Path

from sqlmodel import Session

from .config import get_settings
from .db import engine, init_db
from .services.ingest import ingest_raw
from .services.resumes import reembed_resumes
from .sources.base import JobQuery
from .sources.boards import load_boards
from .sources.registry import build_sources
from .sources.seed import SeedSource


def cmd_ingest(args: argparse.Namespace) -> None:
    init_db()
    settings = get_settings()
    if args.live:
        sources = build_sources(load_boards(args.boards or settings.boards_path))
        raw_jobs = [job for source in sources for job in source.fetch(JobQuery())]
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
