from app.services.ingest import ingest_raw
from app.sources.base import RawJob


def raw(**overrides):
    data = {
        "source": "greenhouse",
        "external_id": "42",
        "title": "AI Engineer",
        "company": "Quince",
        "location": "Bengaluru, India",
        "url": "https://boards.greenhouse.io/quince/jobs/42",
    }
    data.update(overrides)
    return RawJob(**data)


def test_same_source_and_external_id_is_not_reinserted_after_a_title_edit(session):
    first = ingest_raw(session, [raw()], embed=False)
    second = ingest_raw(session, [raw(title="Senior AI Engineer")], embed=False)

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.skipped == 1


def test_same_job_from_two_sources_is_deduped_by_fingerprint(session):
    first = ingest_raw(session, [raw(source="greenhouse", external_id="1")], embed=False)
    second = ingest_raw(session, [raw(source="keka", external_id="2")], embed=False)
    assert first.inserted == 1
    assert second.inserted == 0


def test_blank_external_id_still_dedupes_by_fingerprint(session):
    first = ingest_raw(session, [raw(source="custom", external_id="")], embed=False)
    second = ingest_raw(session, [raw(source="custom", external_id="")], embed=False)
    assert first.inserted == 1
    assert second.skipped == 1
