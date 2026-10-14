"""Tests for PDF and PPTX parsers (skipped when deps are not installed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.rag.parsers import parse_document, parse_pdf, parse_pptx


def _make_pdf(path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hello from StudyQuiz AI. PDF parsing extracts this.")
    page = document.new_page()
    page.insert_text((72, 72), "This sentence lives on page two and must be found too.")
    document.save(str(path))
    document.close()


def _make_pptx(path: Path) -> None:
    pptx = pytest.importorskip("pptx")
    presentation = pptx.Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    slide.shapes.title.text = "Slide Title Text"
    slide.placeholders[1].text = "Slide body with important facts."
    slide.notes_slide.notes_text_frame.text = "Speaker note: remember this detail."
    presentation.save(str(path))


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    _make_pdf(path)
    return path


@pytest.fixture()
def sample_pptx(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pptx"
    _make_pptx(path)
    return path


def test_parse_pdf_extracts_all_pages(sample_pdf: Path) -> None:
    pages = parse_pdf(sample_pdf)
    assert [p.page_number for p in pages] == [1, 2]
    combined = " ".join(p.text for p in pages)
    assert "Hello from StudyQuiz AI" in combined
    assert "page two" in combined


def test_parse_pptx_extracts_text_and_notes(sample_pptx: Path) -> None:
    pages = parse_pptx(sample_pptx)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    combined = pages[0].text
    assert "Slide Title Text" in combined
    assert "important facts" in combined
    assert "Speaker note: remember this detail." in combined


def test_parse_document_dispatches_by_type(sample_pdf: Path, sample_pptx: Path) -> None:
    assert parse_document(sample_pdf, "pdf")[0].page_number == 1
    assert parse_document(sample_pptx, "pptx")[0].page_number == 1


def test_parse_document_rejects_unknown_type(sample_pdf: Path) -> None:
    with pytest.raises(ValueError):
        parse_document(sample_pdf, "docx")