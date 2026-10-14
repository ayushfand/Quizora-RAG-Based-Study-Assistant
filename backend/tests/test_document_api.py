"""API smoke tests for document upload / list / delete endpoints."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _make_pdf_bytes() -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Photosynthesis converts light into chemical energy. Chloroplasts are the site of this process.")
    payload = document.tobytes()
    document.close()
    return payload


def test_upload_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400


def test_upload_list_get_delete_flow(client: TestClient) -> None:
    payload = _make_pdf_bytes()
    response = client.post(
        "/api/documents",
        files={"file": ("study_notes.pdf", io.BytesIO(payload), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["original_filename"] == "study_notes.pdf"
    assert document["status"] in {"processing", "ready", "failed"}
    document_id = document["id"]
    assert document["file_size"] == len(payload)

    listing = client.get("/api/documents").json()
    assert any(item["id"] == document_id for item in listing)

    detail = client.get(f"/api/documents/{document_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == document_id

    deleted = client.delete(f"/api/documents/{document_id}")
    assert deleted.status_code == 204

    listing_after = client.get("/api/documents").json()
    assert all(item["id"] != document_id for item in listing_after)


def test_get_missing_document_returns_404(client: TestClient) -> None:
    response = client.get("/api/documents/999999")
    assert response.status_code == 404