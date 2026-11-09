import json

import httpx

from app.sources.base import JobQuery
from app.sources.boards import Board
from app.sources.darwinbox import DarwinboxSource


def page(rows, total):
    return {"status": "success", "data": rows, "job_counts": total}


ROW = {
    "id": "db-1",
    "title": " Data Analyst ",
    "jd": "&amp;lt;p&amp;gt;SQL and dashboards&amp;lt;/p&amp;gt;",
    "country": "India",
    "officelocations_without_area": ["Mumbai, Maharashtra\r, India"],
    "is_remote": 0,
    "posted_on": 1790812800,
}


def test_fetch_maps_darwinbox_posting_and_pages():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body["page"])
        if body["page"] == 1:
            return httpx.Response(200, json=page([ROW], 1))
        return httpx.Response(200, json=page([], 1))

    source = DarwinboxSource(
        [Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    jobs = source.fetch(JobQuery())

    assert calls == [1, 2]
    job = jobs[0]
    assert job.source == "darwinbox"
    assert job.external_id == "pwc.darwinbox.com:db-1"
    assert job.title == "Data Analyst"
    assert job.company == "PwC India"
    assert job.location == "Mumbai, Maharashtra, India"
    assert job.description == "SQL and dashboards"
    assert job.url == "https://pwc.darwinbox.com/ms/candidatev2/main/careers/jobDetails/db-1"
    assert job.salary_min is None


def test_count_mismatch_does_not_discard_valid_postings():
    def handler(request):
        board = request.url.host.split(".")[0]
        if board == "broken":
            return httpx.Response(200, json=page([], 99))
        body = json.loads(request.content)
        if body["page"] == 1:
            return httpx.Response(200, json=page([ROW], 1))
        return httpx.Response(200, json=page([], 1))

    source = DarwinboxSource(
        [
            Board("darwinbox", "broken.darwinbox.com", "Broken"),
            Board("darwinbox", "pwc.darwinbox.com", "PwC India"),
        ],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert [job.company for job in source.fetch(JobQuery())] == ["PwC India"]


def test_bad_host_makes_no_request():
    def handler(request):
        raise AssertionError("must not call the network")

    source = DarwinboxSource(
        [Board("darwinbox", "evil.example.com", "Evil")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert source.fetch(JobQuery()) == []


def test_posting_without_title_is_skipped():
    payload = page([{"id": "x", "title": "  "}], 1)
    source = DarwinboxSource(
        [Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    )
    assert source.fetch(JobQuery()) == []


def test_a_skipped_row_does_not_discard_valid_postings():
    def handler(request):
        body = json.loads(request.content)
        if body["page"] == 1:
            return httpx.Response(200, json=page([ROW, {"id": "bad", "title": "  "}], 2))
        return httpx.Response(200, json=page([], 2))

    source = DarwinboxSource(
        [Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert [job.external_id for job in source.fetch(JobQuery())] == [
        "pwc.darwinbox.com:db-1"
    ]


def test_endless_pagination_is_bounded():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body["page"])
        row = dict(ROW, id=f"db-{body['page']}")
        return httpx.Response(200, json=page([row], 999_999))

    source = DarwinboxSource(
        [Board("darwinbox", "pwc.darwinbox.com", "PwC India")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert source.fetch(JobQuery()) == []
    assert len(calls) == 50
