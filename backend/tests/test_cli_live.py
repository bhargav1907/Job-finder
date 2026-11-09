from app.cli import build_parser
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
