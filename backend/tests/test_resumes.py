import numpy as np
import pytest
from sqlmodel import select

from app.models import Resume
from app.services import resumes as service
from tests.factories import make_profile


@pytest.fixture
def fake_embed(monkeypatch):
    monkeypatch.setattr(
        service,
        "embed_texts",
        lambda texts: np.ones((len(texts), 384), dtype=np.float32),
    )


def test_creates_resume_with_profile_and_embedding(session, fake_embed, monkeypatch):
    parsed = make_profile()
    monkeypatch.setattr(
        service, "parse_resume_text", lambda text, client=None: (parsed, "qwen3:4b")
    )
    row, created = service.create_resume(session, "priya.txt", b"Priya Sharma\nPython")
    assert created is True
    assert row.id is not None
    assert row.parse_model == "qwen3:4b"
    assert row.profile["name"] == "Priya Sharma"
    assert len(row.embedding) == 384 * 4
    assert row.content_hash


def test_same_text_is_not_parsed_twice(session, fake_embed, monkeypatch):
    calls = []
    parsed = make_profile()

    def fake_parse(text, client=None):
        calls.append(text)
        return parsed, "qwen3:4b"

    monkeypatch.setattr(service, "parse_resume_text", fake_parse)
    first, created_first = service.create_resume(session, "a.txt", b"Priya   Sharma\nPython")
    second, created_second = service.create_resume(session, "b.txt", b"Priya Sharma\nPython")
    assert created_first is True and created_second is False
    assert first.id == second.id
    assert len(calls) == 1
    assert len(session.exec(select(Resume)).all()) == 1


def test_embedding_text_includes_highlights_and_certifications(session, monkeypatch):
    captured = {}
    profile = make_profile()
    profile.experience[0].highlights.append("Built a RAG pipeline with LangChain")
    profile.certifications.append("AWS Certified Machine Learning")
    profile.preferred_locations = ["Bengaluru", "remote"]

    def fake_embed(texts):
        captured["text"] = texts[0]
        return np.ones((len(texts), 384), dtype=np.float32)

    monkeypatch.setattr(service, "embed_texts", fake_embed)
    monkeypatch.setattr(
        service, "parse_resume_text", lambda text, client=None: (profile, "qwen3:4b")
    )
    service.create_resume(session, "priya.txt", b"Priya Sharma\nPython")

    text = captured["text"]
    assert "RAG pipeline" in text
    assert "AWS Certified Machine Learning" in text
    assert "Bengaluru" in text


def test_reembed_resumes_recomputes_every_stored_vector(session, monkeypatch):
    profile = make_profile()
    monkeypatch.setattr(
        service, "embed_texts", lambda texts: np.ones((len(texts), 384), dtype=np.float32)
    )
    monkeypatch.setattr(
        service, "parse_resume_text", lambda text, client=None: (profile, "qwen3:4b")
    )
    row, _ = service.create_resume(session, "priya.txt", b"Priya Sharma\nPython")

    monkeypatch.setattr(
        service, "embed_texts", lambda texts: np.full((len(texts), 384), 2.0, dtype=np.float32)
    )
    assert service.reembed_resumes(session) == 1
    session.refresh(row)
    assert np.allclose(np.frombuffer(row.embedding, dtype=np.float32), 2.0)
