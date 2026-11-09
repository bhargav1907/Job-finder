import httpx

from app.sources.base import JobQuery
from app.sources.boards import Board
from app.sources.greenhouse import GreenhouseSource

PAYLOAD = {
    "jobs": [
        {
            "id": 42,
            "title": "Senior AI Engineer",
            "absolute_url": "https://boards.greenhouse.io/quince/jobs/42",
            "updated_at": "2026-10-01T10:00:00Z",
            "content": "&lt;p&gt;Build &amp;amp; ship&lt;/p&gt;",
            "location": {"name": "Bengaluru, India"},
        }
    ]
}


def test_fetch_maps_a_greenhouse_posting():
    def handler(request):
        assert request.url.params["content"] == "true"
        assert request.url.params["pay_transparency"] == "true"
        return httpx.Response(200, json=PAYLOAD)

    source = GreenhouseSource(
        [Board("greenhouse", "quince", "Quince")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    jobs = source.fetch(JobQuery())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "greenhouse"
    assert job.external_id == "quince:42"
    assert job.title == "Senior AI Engineer"
    assert job.company == "Quince"
    assert job.location == "Bengaluru, India"
    assert job.description == "Build & ship"
    assert job.url == "https://boards.greenhouse.io/quince/jobs/42"
    assert job.salary_min is None and job.salary_max is None


def test_one_failing_board_does_not_stop_the_others():
    def handler(request):
        if "/broken/" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json=PAYLOAD)

    source = GreenhouseSource(
        [Board("greenhouse", "broken", "Broken"), Board("greenhouse", "quince", "Quince")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert [job.company for job in source.fetch(JobQuery())] == ["Quince"]


def test_numeric_location_name_is_kept_as_text():
    payload = {"jobs": [dict(PAYLOAD["jobs"][0], location={"name": 123})]}
    source = GreenhouseSource(
        [Board("greenhouse", "quince", "Quince")],
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    )
    assert source.fetch(JobQuery())[0].location == "123"


def test_posting_without_id_or_title_is_skipped():
    payload = {"jobs": [{"id": 1, "title": "", "location": {"name": ""}}, {"title": "No id"}]}
    source = GreenhouseSource(
        [Board("greenhouse", "quince", "Quince")],
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    )
    assert source.fetch(JobQuery()) == []
