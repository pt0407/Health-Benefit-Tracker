"""Standing gate: the real program records and their source sidecars must pass strict validation."""
import sys

from config import DATA_DIR

sys.path.insert(0, str(DATA_DIR / "scripts"))
import parse_programs as pp  # noqa: E402

REQUIRED_IDS = {
    "snap_federal", "medicaid_federal", "wic_federal", "liheap_federal",
    "medicare_extra_help_federal", "ssdi_federal",
    "chip_tx", "childrens_medicaid_tx", "medicaid_pregnant_women_tx", "chip_perinatal_tx",
    "emergency_medicaid_tx", "medicaid_elderly_disabled_tx", "tanf_tx", "unemployment_benefits_tx",
    "medicaid_parents_caretakers_tx", "medicaid_buy_in_tx", "primary_health_care_tx",
    "vocational_rehabilitation_tx", "child_care_services_tx", "weatherization_assistance_tx",
    "scsep_tx", "senior_meals_tx",
    "head_start_federal", "early_head_start_federal", "school_breakfast_federal", "summer_meals_federal",
    "medicare_federal", "social_security_retirement_federal", "ssi_federal", "eitc_federal",
    "child_tax_credit_federal", "vita_free_tax_help_federal", "health_centers_federal", "job_corps_federal",
    "title_x_family_planning_federal", "legal_aid_lsc_federal", "ticket_to_work_federal",
    "medicare_savings_programs_tx", "family_planning_program_tx", "nurse_family_partnership_tx",
    "child_support_services_tx", "texas_prekindergarten_tx", "independent_living_services_tx",
    "work_incentives_planning_federal", "texas_benefits_counseling_tx",
    "lifeline_federal", "csfp_federal", "child_dependent_care_credit_federal",
    "national_school_lunch_federal", "credit_for_other_dependents_federal", "texas_vaccines_for_children_tx",
}


def test_validator_reports_zero_problems():
    count, problems, _unconfirmed = pp.validate(DATA_DIR)
    assert problems == []
    assert count == len(REQUIRED_IDS)


def test_required_program_ids_present():
    import json

    ids = set()
    for path in (DATA_DIR / "programs").glob("*_programs.json"):
        ids |= {r["program_id"] for r in json.loads(path.read_text(encoding="utf-8"))}
    assert REQUIRED_IDS <= ids


def test_every_programs_file_has_a_sources_file():
    for path in (DATA_DIR / "programs").glob("*_programs.json"):
        sidecar = DATA_DIR / "sources" / path.name.replace("_programs.json", "_sources.json")
        assert sidecar.exists(), f"missing {sidecar.name}"


def test_no_numeric_field_marked_unconfirmed():
    _count, _problems, unconfirmed = pp.validate(DATA_DIR)
    numeric = [u for u in unconfirmed if not str(u[1]).startswith("eligibility.") or "pct" in str(u[1]) or "age" in str(u[1])]
    assert numeric == []
    for pid, field, f in pp.iter_sidecar_fields(DATA_DIR):
        if f.get("unconfirmed"):
            assert field in pp.BOOL_FIELDS, f"{pid} {field} unconfirmed but not a boolean field"


# ---- Phase 2: estimate markers and null reasons on the real data ----

import json  # noqa: E402

NUMERIC_FIELDS = (
    "eligibility.income_limit_pct_fpl",
    "estimated_monthly_value_usd",
    "processing_time_days",
)

# Phase 2 fill list: every one of these is either an estimate or an explained null.
FILL_LIST = [
    ("medicaid_elderly_disabled_tx", "eligibility.income_limit_pct_fpl"),
    ("tanf_tx", "eligibility.income_limit_pct_fpl"),
    ("medicaid_federal", "estimated_monthly_value_usd"),
    ("liheap_federal", "estimated_monthly_value_usd"),
    ("medicare_extra_help_federal", "estimated_monthly_value_usd"),
    ("chip_tx", "estimated_monthly_value_usd"),
    ("childrens_medicaid_tx", "estimated_monthly_value_usd"),
    ("medicaid_pregnant_women_tx", "estimated_monthly_value_usd"),
    ("chip_perinatal_tx", "estimated_monthly_value_usd"),
    ("emergency_medicaid_tx", "estimated_monthly_value_usd"),
    ("medicaid_elderly_disabled_tx", "estimated_monthly_value_usd"),
    ("tanf_tx", "estimated_monthly_value_usd"),
    ("unemployment_benefits_tx", "estimated_monthly_value_usd"),
    ("liheap_federal", "processing_time_days"),
    ("medicare_extra_help_federal", "processing_time_days"),
    ("medicaid_parents_caretakers_tx", "eligibility.income_limit_pct_fpl"),
    ("medicaid_parents_caretakers_tx", "estimated_monthly_value_usd"),
    ("medicaid_buy_in_tx", "eligibility.income_limit_pct_fpl"),
    ("child_care_services_tx", "eligibility.income_limit_pct_fpl"),
    ("weatherization_assistance_tx", "estimated_monthly_value_usd"),
    ("scsep_tx", "estimated_monthly_value_usd"),
]

HEALTH_COVERAGE_IDS = {
    "medicaid_federal", "chip_tx", "childrens_medicaid_tx", "medicaid_pregnant_women_tx",
    "chip_perinatal_tx", "medicaid_elderly_disabled_tx", "emergency_medicaid_tx",
    "medicaid_parents_caretakers_tx", "medicaid_buy_in_tx", "primary_health_care_tx",
    "medicare_federal", "health_centers_federal", "title_x_family_planning_federal",
    "medicare_savings_programs_tx", "family_planning_program_tx", "nurse_family_partnership_tx",
    "texas_vaccines_for_children_tx",
}


def _records() -> dict:
    out = {}
    for path in sorted((DATA_DIR / "programs").glob("*_programs.json")):
        for rec in json.loads(path.read_text(encoding="utf-8")):
            out[rec["program_id"]] = rec
    return out


def _sidecars() -> dict:
    out = {}
    for path in sorted((DATA_DIR / "sources").glob("*_sources.json")):
        out.update(json.loads(path.read_text(encoding="utf-8")))
    return out


def _value(rec: dict, field: str):
    if field.startswith("eligibility."):
        return rec["eligibility"][field.split(".", 1)[1]]
    return rec[field]


def test_fill_list_is_estimated_or_explained_null():
    recs, side = _records(), _sidecars()
    for pid, field in FILL_LIST:
        entry = side[pid]["fields"].get(field)
        assert entry is not None, f"{pid} {field} has no sidecar entry"
        if _value(recs[pid], field) is None:
            assert entry.get("null_reason") in {"no_income_test", "not_applicable", "no_official_basis"}, (pid, field)
            assert entry.get("note"), (pid, field)
        else:
            assert entry.get("estimated") is True, (pid, field)
            assert isinstance(entry.get("estimate"), dict), (pid, field)


def test_marked_estimates_recompute_through_the_validator():
    # The validator evaluates every formula with its safe evaluator and compares to the record value.
    _count, problems, _u = pp.validate(DATA_DIR)
    assert problems == []
    marked = {(pid, field) for pid, field, f in pp.iter_sidecar_fields(DATA_DIR) if f.get("estimated") is True}
    listed = {(pid, field) for pid, field, _m in pp.estimated_fields(DATA_DIR)}
    assert marked == listed
    assert {x for x in FILL_LIST if _value(_records()[x[0]], x[1]) is not None} <= marked


def test_no_income_test_programs_use_null_not_zero():
    recs, side = _records(), _sidecars()
    for pid in ("unemployment_benefits_tx", "ssdi_federal"):
        assert recs[pid]["eligibility"]["income_limit_pct_fpl"] is None
        assert side[pid]["fields"]["eligibility.income_limit_pct_fpl"]["null_reason"] == "no_income_test"
    for pid, rec in recs.items():
        assert rec["eligibility"]["income_limit_pct_fpl"] != 0, pid


def test_estimated_records_say_estimate_in_description():
    recs = _records()
    estimated_ids = {pid for pid, _f, _m in pp.estimated_fields(DATA_DIR)}
    assert estimated_ids
    for pid in estimated_ids:
        assert "estimate" in recs[pid]["description"].lower(), pid


def test_health_coverage_values_are_spending_not_cash():
    side = _sidecars()
    seen = 0
    for pid in HEALTH_COVERAGE_IDS:
        entry = side[pid]["fields"].get("estimated_monthly_value_usd", {})
        if entry.get("estimated") is True:
            seen += 1
            est = entry["estimate"]
            assert est["method"] == "per_enrollee_spending", pid
            assert "not cash" in est["represents"].lower(), pid
    assert seen >= 6


def _number_forms(value) -> set:
    forms = {str(value), f"{value:,}"}
    if isinstance(value, float):
        forms |= {f"{value:.2f}", f"{value:,.2f}", f"{value:.1f}", f"{value:,.1f}"}
        if value == int(value):
            forms |= {str(int(value)), f"{int(value):,}"}
    return forms


def test_unmarked_numeric_values_appear_in_sidecar_text():
    recs, side = _records(), _sidecars()
    for pid, rec in recs.items():
        for field in NUMERIC_FIELDS:
            value = _value(rec, field)
            entry = side[pid]["fields"].get(field, {})
            if value is None or entry.get("estimated") is True:
                continue
            text = f"{entry.get('evidence', '')} {entry.get('note', '')}"
            assert any(form in text for form in _number_forms(value)), f"{pid} {field}={value} not in sidecar text"
