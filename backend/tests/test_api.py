from fastapi.testclient import TestClient

from main import app
from routers.benefits import load_programs

client = TestClient(app)

SAMPLE_PROFILE = {
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


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_match_returns_contract_shape():
    res = client.post("/api/match", json=SAMPLE_PROFILE)
    assert res.status_code == 200
    body = res.json()
    assert body["program_count"] == len(body["matched_programs"])
    assert {"total_estimated_annual_value", "warnings", "generated_at"} <= body.keys()


def test_match_rejects_invalid_profile():
    res = client.post("/api/match", json={**SAMPLE_PROFILE, "household_size": 0})
    assert res.status_code == 422


def test_program_data_matches_schema():
    # Raises a ValidationError if any data/programs/*.json entry is malformed.
    programs = load_programs()
    ids = [p.program_id for p in programs]
    assert len(ids) == len(set(ids)), "duplicate program_id"


def test_get_program():
    assert client.get("/api/programs/snap_federal").status_code == 200
    assert client.get("/api/programs/nope").status_code == 404
