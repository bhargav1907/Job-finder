import httpx

from app.sources.base import JobQuery
from app.sources.boards import Board
from app.sources.keka import KekaSource

PAYLOAD = [
    {
        "id": 7,
        "title": "Backend Developer",
        "description": "<p>Python &amp; SQL</p>",
        "jobType": 2,
        "publishedOn": "2026-10-02T08:30:00Z",
        "jobLocations": [{"city": "Pune", "state": "Maharashtra", "countryName": "India"}],
    }
]


def test_fetch_maps_a_keka_posting():
    def handler(request):
        assert str(request.url) == "https://softobiz.keka.com/careers/api/jobs/default/active"
        return httpx.Response(200, json=PAYLOAD)

    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz")],
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    job = source.fetch(JobQuery())[0]

    assert job.source == "keka"
    assert job.external_id == "softobiz:7"
    assert job.title == "Backend Developer"
    assert job.company == "Softobiz"
    assert job.location == "Pune, Maharashtra, India"
    assert job.description == "Python & SQL"
    assert job.url == "https://softobiz.keka.com/careers/jobdetails/7"
    assert job.salary_min is None and job.salary_max is None


def test_malformed_keka_board_is_skipped():
    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz")],
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"oops": True})
            )
        ),
    )
    assert source.fetch(JobQuery()) == []


def test_two_boards_with_the_same_raw_id_stay_distinct():
    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz"), Board("keka", "mosaicwellness", "Mosaic")],
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=PAYLOAD))
        ),
    )
    assert [job.external_id for job in source.fetch(JobQuery())] == [
        "softobiz:7",
        "mosaicwellness:7",
    ]


def test_numeric_timestamp_does_not_abort_the_board():
    payload = [dict(PAYLOAD[0], publishedOn=1790812800)]
    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz")],
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    )
    jobs = source.fetch(JobQuery())
    assert len(jobs) == 1
    assert jobs[0].posted_at is None


def test_keka_posting_without_title_is_skipped():
    payload = [{"id": 8, "title": "", "jobLocations": []}]
    source = KekaSource(
        [Board("keka", "softobiz", "Softobiz")],
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    )
    assert source.fetch(JobQuery()) == []
