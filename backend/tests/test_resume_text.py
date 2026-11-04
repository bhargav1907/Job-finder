import io
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

from app.services.resume_text import EmptyResume, UnsupportedFormat, extract_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_extracts_utf8_txt():
    text = extract_text("resume.txt", "Priya Sharma\nPython, SQL".encode())
    assert "Priya Sharma" in text
    assert "Python, SQL" in text


def test_falls_back_to_latin1():
    assert "Café" in extract_text("resume.txt", "Café\nPython".encode("latin-1"))


def test_normalizes_whitespace():
    text = extract_text("resume.txt", b"Priya   Sharma\n\n\n\nPython\tSQL")
    assert "Priya Sharma" in text
    assert "\n\n\n" not in text


def test_caps_long_text():
    text = extract_text("resume.txt", b"x" * 60_000, max_chars=1_000)
    assert len(text) <= 1_000


def test_uppercase_pdf_suffix_is_supported():
    data = (FIXTURES / "sample_resume.pdf").read_bytes()
    assert "Priya Sharma" in extract_text("Resume.PDF", data)


def test_extracts_pdf_text():
    data = (FIXTURES / "sample_resume.pdf").read_bytes()
    assert "Priya Sharma" in extract_text("resume.pdf", data)


def test_pdf_without_text_raises_empty():
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(buffer)
    with pytest.raises(EmptyResume):
        extract_text("blank.pdf", buffer.getvalue())


def test_corrupt_pdf_raises_empty():
    with pytest.raises(EmptyResume):
        extract_text("bad.pdf", b"not a pdf")


def test_extracts_docx_paragraphs_and_tables():
    document = Document()
    document.add_paragraph("Priya Sharma")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Python"
    table.cell(0, 1).text = "SQL"
    buffer = io.BytesIO()
    document.save(buffer)
    text = extract_text("resume.docx", buffer.getvalue())
    assert "Priya Sharma" in text
    assert "Python" in text and "SQL" in text


def test_empty_file_raises_empty():
    with pytest.raises(EmptyResume):
        extract_text("resume.txt", b"   ")


def test_unsupported_suffix_raises():
    with pytest.raises(UnsupportedFormat):
        extract_text("resume.rtf", b"hello")
