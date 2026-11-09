"""Small, deterministic helpers shared by the ATS adapters."""

import html
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

_BLOCK_TAGS = {
    "address",
    "article",
    "blockquote",
    "br",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}
_SKIP_TAGS = {"script", "style"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        self.parts.append("\n" if tag in _BLOCK_TAGS else " ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_text(value: str, unescape_times: int = 1) -> str:
    """Render HTML as plain text. Safe for once- and twice-encoded bodies."""
    text = value or ""
    for _ in range(max(0, unescape_times)):
        text = html.unescape(text)

    parser = _TextExtractor()
    parser.feed(text)
    parser.close()

    rendered = "".join(parser.parts)
    rendered = re.sub(r"[^\S\n]+", " ", rendered)
    rendered = re.sub(r"\s*\n\s*", "\n", rendered)
    return rendered.strip()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_epoch_seconds(value: int | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (OverflowError, OSError, TypeError, ValueError):
        return None


def join_nonempty(*parts: str) -> str:
    return ", ".join(part.strip() for part in parts if part and part.strip())
