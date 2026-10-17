"""Tests for the income what-if endpoint and grid."""

from fastapi.testclient import TestClient

from main import app
from matching.eligibility_matcher import fpl_for_household
from matching.income_scenarios import MAX_POINTS, income_grid
from tests.test_api import SAMPLE_PROFILE

client = TestClient(app)


def test_grid_includes_current_income_and_reaches_four_times_fpl():
    fpl = fpl_for_household(4)
    grid = income_grid(32_123, fpl)
    assert 32_123 in grid
    assert grid[0] == 0 and grid[-1] >= 4 * fpl
    assert grid == sorted(grid) and len(grid) <= MAX_POINTS + 2


def test_grid_extends_past_a_high_income():
    grid = income_grid(500_000, fpl_for_household(1))
    assert grid[-1] >= 750_000 and len(grid) <= MAX_POINTS + 2


def test_endpoint_returns_scenarios_consistent_with_programs():
    res = client.post("/api/income-scenarios", json=SAMPLE_PROFILE)
    assert res.status_code == 200
    data = res.json()
    ids = {p["program_id"] for p in data["programs"]}
    incomes = [s["annual_income"] for s in data["scenarios"]]
    assert incomes == sorted(incomes)
    assert SAMPLE_PROFILE["annual_income"] in incomes
    for s in data["scenarios"]:
        assert {m["program_id"] for m in s["matches"]} <= ids
        assert s["program_count"] == len(s["matches"])


def test_fewer_income_tested_programs_at_high_income():
    data = client.post("/api/income-scenarios", json=SAMPLE_PROFILE).json()
    low, high = data["scenarios"][0], data["scenarios"][-1]
    assert high["program_count"] < low["program_count"]
    assert high["total_estimated_monthly_value"] <= low["total_estimated_monthly_value"]


def test_health_programs_carry_no_dollar_value():
    data = client.post("/api/income-scenarios", json=SAMPLE_PROFILE).json()
    assert all(p["monthly_value_usd"] == 0 for p in data["programs"] if p["category"] == "health")


def test_endpoint_is_gzipped_for_clients_that_accept_it():
    res = client.post("/api/income-scenarios", json=SAMPLE_PROFILE, headers={"Accept-Encoding": "gzip"})
    assert res.headers.get("content-encoding") == "gzip"


def test_endpoint_rejects_bad_profile():
    assert client.post("/api/income-scenarios", json={"state": "TX"}).status_code == 422
