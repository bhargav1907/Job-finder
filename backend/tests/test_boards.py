import json

import pytest

from app.config import PROJECT_ROOT
from app.sources.boards import Board, BoardConfigError, load_boards


def write(tmp_path, rows):
    path = tmp_path / "boards.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_load_boards_reads_provider_board_company(tmp_path):
    path = write(tmp_path, [{"provider": "keka", "board": "softobiz", "company": "Softobiz"}])
    assert load_boards(path) == [Board("keka", "softobiz", "Softobiz")]


def test_load_boards_rejects_unknown_provider(tmp_path):
    path = write(tmp_path, [{"provider": "naukri", "board": "x", "company": "X"}])
    with pytest.raises(BoardConfigError, match="unknown provider"):
        load_boards(path)


def test_load_boards_rejects_bad_darwinbox_host(tmp_path):
    path = write(tmp_path, [{"provider": "darwinbox", "board": "evil.com/x", "company": "X"}])
    with pytest.raises(BoardConfigError, match="darwinbox host"):
        load_boards(path)


def test_load_boards_rejects_duplicate_provider_board(tmp_path):
    row = {"provider": "greenhouse", "board": "quince", "company": "Quince"}
    path = write(tmp_path, [row, row])
    with pytest.raises(BoardConfigError, match="duplicate"):
        load_boards(path)


def test_committed_board_file_is_valid():
    boards = load_boards(PROJECT_ROOT / "data" / "boards.json")
    assert {board.provider for board in boards} == {"darwinbox", "greenhouse", "keka"}
    assert len(boards) >= 18
