"""python -m app.cli ingest"""

import argparse
import json

from sqlmodel import Session

from .config import get_settings
from .db import engine, init_db
from .services.ingest import ingest_raw
from .sources.base import JobQuery
from .sources.seed import SeedSource


def cmd_ingest(args: argparse.Namespace) -> None:
    init_db()
    settings = get_settings()
    raw_jobs = SeedSource(settings.seed_path).fetch(JobQuery())
    with Session(engine) as session:
        result = ingest_raw(session, raw_jobs, embed=not args.no_embed)
    print(json.dumps(result.as_dict(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Load the seed corpus")
    ingest.add_argument("--no-embed", action="store_true", help="Skip embedding")
    ingest.set_defaults(func=cmd_ingest)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
