import pytest

from app.cli import build_parser, fetch_live
from app.sources.base import RawJob
from app.sources.boards import Board
from app.sources.darwinbox import DarwinboxSource
from app.sources.greenhouse import GreenhouseSource
from app.sources.keka import KekaSource
from app.sources.registry import build_sources


def test_build_sources_groups_by_provider():
    boards = [
        Board("greenhouse", "quince", "Quince"),
        Board("keka", "softobiz", "Softobiz"),
        Board("darwinbox", "pwc.darwinbox.com", "PwC India"),
    ]
    sources = build_sources(boards)
    assert [type(source) for source in sources] == [
        GreenhouseSource,
        KekaSource,
        DarwinboxSource,
    ]
    assert [len(source.boards) for source in sources] == [1, 1, 1]


def test_ingest_defaults_to_seed_and_accepts_live():
    parser = build_parser()
    assert parser.parse_args(["ingest"]).live is False
    args = parser.parse_args(["ingest", "--live", "--no-embed"])
    assert args.live is True and args.no_embed is True


class FakeSource:
    def __init__(self, name, jobs):
        self.name = name
        self.jobs = jobs

    def fetch(self, query):
        return self.jobs


def raw(external_id):
    return RawJob(
        source="fake",
        external_id=external_id,
        title="AI Engineer",
        company="Quince",
    )


def test_fetch_live_collects_jobs_from_every_source():
    jobs = fetch_live(
        [
            FakeSource("a", [raw("a:1")]),
            FakeSource("b", [raw("b:1")]),
        ]
    )
    assert [job.external_id for job in jobs] == ["a:1", "b:1"]


def test_fetch_live_fails_when_every_board_is_empty():
    with pytest.raises(SystemExit, match="no live postings"):
        fetch_live([FakeSource("a", []), FakeSource("b", [])])
