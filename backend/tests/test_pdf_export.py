"""Tests for the application-worksheet PDF export."""

import io
import json

from fastapi.testclient import TestClient
from PyPDF2 import PdfReader

from config import FIXTURES_DIR
from main import app

client = TestClient(app)

PROFILE = {
    "state": "TX",
    "household_size": 4,
    "annual_income": 32000,
    "income_bracket": "30-50k",
    "employment_status": "employed",
    "age": 34,
    "has_children": True,
    "children_ages": [6, 8],
    "is_pregnant": False,
    "has_disability": False,
    "insurance_status": "uninsured",
    "citizenship": "citizen",
}

RESULT = json.loads((FIXTURES_DIR / "sample_match_response.json").read_text())


def _pdf_text(pdf_bytes: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf_bytes)).pages)


def test_export_pdf_returns_a_pdf():
    res = client.post("/api/export/pdf", json={"profile": PROFILE, "result": RESULT})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    assert "attachment" in res.headers["content-disposition"]


def test_pdf_contains_answers_and_programs():
    res = client.post("/api/export/pdf", json={"profile": PROFILE, "result": RESULT})
    text = _pdf_text(res.content)
    assert "Your answers" in text
    assert "SNAP" in text
    assert "yourtexasbenefits.com" in text
    assert "not an official application" in text


def test_export_pdf_rejects_bad_payload():
    res = client.post("/api/export/pdf", json={"profile": {"state": "TX"}, "result": RESULT})
    assert res.status_code == 422
