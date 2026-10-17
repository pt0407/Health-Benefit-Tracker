"""The deterministic pre-screen behind the insurance agent."""

import json

from agents.insurance_agent import InsuranceAgent, compute_facts
from agents.screening import (ACA, CHIP_PERINATAL, EMERGENCY, EXTRA_HELP, MEDICARE, MEPD,
                              PREGNANT_WOMEN, identify)
from models.user_profile import UserProfile
from tests.test_insurance_agent import fake_client

BASE = dict(state="TX", is_pregnant=False, has_disability=False, citizenship="citizen",
            has_children=False, children_ages=[], employment_status="employed",
            insurance_status="uninsured")


def facts(**kw):
    f = compute_facts(UserProfile(**{**BASE, **kw}))
    return (f, {p["program"] for p in f["programs_to_consider"]},
            {p["program"] for p in f["ruled_out"]}, {t["threshold"] for t in f["thresholds"]})


def test_pregnant_non_citizen_gets_perinatal_and_emergency_only():
    _, consider, ruled_out, _ = facts(household_size=2, annual_income=34600, age=25,
                                      is_pregnant=True, citizenship="not_citizen")
    assert {CHIP_PERINATAL, EMERGENCY} <= consider
    assert {PREGNANT_WOMEN, ACA} <= ruled_out
    assert not consider & ruled_out


def test_no_medicare_threshold_for_young_adult():
    _, consider, _, thresholds = facts(household_size=2, annual_income=34600, age=25)
    assert "Medicare Extra Help" not in thresholds
    assert EXTRA_HELP not in consider


def test_disabled_adult_gets_medicare_route_and_conditional_gap():
    f, consider, ruled_out, _ = facts(household_size=1, annual_income=14500, age=50,
                                      has_disability=True, receiving_disability_benefits=True,
                                      employment_status="unemployed")
    assert {MEPD, MEDICARE} <= consider
    assert ACA in ruled_out
    assert f["coverage_gap"] == "only if MEPD and Medicare do not apply"


def test_plain_coverage_gap():
    f, consider, _, _ = facts(household_size=1, annual_income=9600, age=42,
                              employment_status="unemployed")
    assert f["coverage_gap"] == "yes"
    assert not consider


def test_child_thresholds_follow_child_ages():
    _, _, _, thresholds = facts(household_size=3, annual_income=32800, age=34,
                                has_children=True, children_ages=[4, 9])
    assert "Children's Medicaid, children 1-5" in thresholds
    assert "Children's Medicaid, children 6-18" in thresholds
    assert "Children's Medicaid, children under 1" not in thresholds


def test_identify_maps_names_and_ids():
    assert identify("CHIP Perinatal (TX)") == CHIP_PERINATAL
    assert identify("CHIP (TX)") != CHIP_PERINATAL
    assert identify("Medicare Part D Extra Help") == EXTRA_HELP
    assert identify("Medicare") == MEDICARE
    assert identify("ACA Marketplace premium tax credits") == ACA
    assert identify("anything", "medicaid_pregnant_women_tx") == PREGNANT_WOMEN


def test_run_drops_programs_the_screen_ruled_out():
    output = {"qualifies_for": [
        {"program": "Medicaid for Pregnant Women (TX)", "confidence": "medium", "reason": "x"},
        {"program": "ACA Marketplace premium tax credits", "confidence": "medium", "reason": "x"},
        {"program": "CHIP Perinatal (TX)", "confidence": "high", "reason": "x"},
    ], "near_threshold_warnings": [], "notes": ""}
    agent = InsuranceAgent(client=fake_client(text=json.dumps(output)), model="test-model")
    profile = UserProfile(**{**BASE, "household_size": 2, "annual_income": 34600, "age": 25,
                             "is_pregnant": True, "citizenship": "not_citizen"})
    assert [p.program for p in agent.run(profile).qualifies_for] == ["CHIP Perinatal (TX)"]
