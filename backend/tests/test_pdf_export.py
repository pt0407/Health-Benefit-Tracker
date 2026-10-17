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


def test_pdf_escapes_markup_and_uses_match_labels():
    result = json.loads(json.dumps(RESULT))
    program = result["matched_programs"][0]
    program["source"] = "Centers for Medicare & Medicaid Services <b>"
    program["application_url"] = "javascript:alert(1)"
    program["confidence"] = "high"
    for other in result["matched_programs"]:
        other["program"] = other["program"].replace("\u2014", "-")  # the fixture's names have dashes
    res = client.post("/api/export/pdf", json={"profile": PROFILE, "result": result})
    assert res.status_code == 200
    text = _pdf_text(res.content)
    assert "Medicare & Medicaid Services <b>" in text
    assert "Strong match" in text
    assert "Civis" in text and "BenefitsFinder" not in text
    assert "\u2014" not in text
    assert b"/URI (javascript" not in res.content


def test_export_pdf_rejects_too_many_programs():
    result = json.loads(json.dumps(RESULT))
    result["matched_programs"] = result["matched_programs"][:1] * 101
    res = client.post("/api/export/pdf", json={"profile": PROFILE, "result": result})
    assert res.status_code == 413
