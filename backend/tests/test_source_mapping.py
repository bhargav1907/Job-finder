from datetime import datetime, timezone

from app.sources.mapping import (
    html_to_text,
    join_nonempty,
    parse_epoch_seconds,
    parse_iso_datetime,
)


def test_html_to_text_unwraps_entities_and_block_tags():
    assert html_to_text("<p>Hello &amp; welcome</p><p>Second<br>line</p>") == (
        "Hello & welcome\nSecond\nline"
    )


def test_html_to_text_drops_script_and_style():
    assert html_to_text("<style>.x{}</style><script>alert(1)</script><b>Build</b> things") == (
        "Build things"
    )


def test_html_to_text_can_decode_twice_encoded_markup():
    assert html_to_text("&amp;lt;p&amp;gt;Hi&amp;lt;/p&amp;gt;", unescape_times=2) == "Hi"


def test_parse_iso_datetime_normalizes_to_utc():
    assert parse_iso_datetime("2026-10-01T10:00:00Z") == datetime(
        2026, 10, 1, 10, tzinfo=timezone.utc
    )
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime(None) is None


def test_parse_epoch_seconds():
    assert parse_epoch_seconds(1790812800) == datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert parse_epoch_seconds(None) is None


def test_join_nonempty_skips_blank_parts():
    assert join_nonempty("Mumbai", "", "India") == "Mumbai, India"
    assert join_nonempty("", "  ", "") == ""
