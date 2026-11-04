import io

import numpy as np
import pytest
from pypdf import PdfWriter

from app.services import resumes as service
from tests.factories import make_profile


@pytest.fixture(autouse=True)
def fake_pipeline(monkeypatch):
    monkeypatch.setattr(
        service,
        "embed_texts",
        lambda texts: np.ones((len(texts), 384), dtype=np.float32),
    )
    monkeypatch.setattr(
        service,
        "parse_resume_text",
        lambda text, client=None: (make_profile(), "qwen3:4b"),
    )


def upload(api, name="priya.txt", content=b"Priya Sharma\nPython"):
    return api.post("/api/resumes", files={"file": (name, content, "text/plain")})


def test_upload_creates_resume(api):
    response = upload(api)
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "priya.txt"
    assert body["profile"]["name"] == "Priya Sharma"
    assert body["parse_model"] == "qwen3:4b"
    assert "text" not in body


def test_duplicate_upload_returns_existing(api):
    first = upload(api)
    second = upload(api, name="copy.txt")
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_get_resume(api):
    created = upload(api).json()
    response = api.get(f"/api/resumes/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_resume_returns_404(api):
    assert api.get("/api/resumes/9999").status_code == 404


def test_unsupported_format_returns_415(api):
    assert upload(api, name="resume.rtf").status_code == 415


def test_empty_file_returns_422(api):
    assert upload(api, content=b"").status_code == 422


def test_scanned_pdf_returns_422(api):
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(buffer)
    assert upload(api, name="scan.pdf", content=buffer.getvalue()).status_code == 422


def test_oversized_file_returns_413(api):
    payload = b"x" * (5 * 1024 * 1024 + 1)
    assert upload(api, content=payload).status_code == 413


def test_uppercase_txt_suffix_is_accepted(api):
    assert upload(api, name="RESUME.TXT").status_code == 201
