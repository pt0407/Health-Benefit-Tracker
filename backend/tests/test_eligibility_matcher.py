"""Tests for the deterministic eligibility matcher (Component 5)."""

from matching.eligibility_matcher import EligibilityMatcher, fpl_for_household
from models.match_result import InsuranceResult, MatchedProgram
from models.user_profile import UserProfile
from routers.benefits import load_programs

PROGRAMS = load_programs()

FAMILY = dict(
    state="TX", household_size=4, annual_income=32000, income_bracket="30-50k",
    employment_status="employed", age=34, has_children=True, children_ages=[6, 8],
    is_pregnant=False, has_disability=False, insurance_status="uninsured",
    citizenship="citizen",
)


def make_matcher(**overrides):
    profile = UserProfile(**{**FAMILY, **overrides})
    return profile, EligibilityMatcher(programs=PROGRAMS)


def matched_ids(result):
    return {p.program_id for p in result.matched_programs}


def test_fpl_2026_values():
    assert fpl_for_household(1) == 15960
    assert fpl_for_household(4) == 33000
    assert fpl_for_household(8) == 55720
    assert fpl_for_household(9) == 55720 + 5680


def test_family_matches_expected_programs():
    profile, matcher = make_matcher()
    result = matcher.match(profile)
    ids = matched_ids(result)
    assert {"snap_federal", "liheap_federal", "medicaid_federal",
            "chip_tx", "childrens_medicaid_tx"} <= ids
    # No child under 5 and not pregnant -> no WIC; employed -> no unemployment.
    assert "wic_federal" not in ids
    assert "unemployment_benefits_tx" not in ids
    assert "tanf_tx" not in ids  # 97% FPL is far above the 8% limit
    assert result.program_count == len(result.matched_programs)


def test_banded_programs_cap_at_medium_confidence():
    _, matcher = make_matcher()
    result = matcher.match(UserProfile(**FAMILY))
    by_id = {p.program_id: p for p in result.matched_programs}
    # SNAP's stored 165% is the top of several bands -> medium, not high.
    assert by_id["snap_federal"].confidence == "medium"
    assert by_id["childrens_medicaid_tx"].confidence == "medium"
    # Single-limit programs can be high.
    assert by_id["liheap_federal"].confidence == "high"
    assert by_id["chip_tx"].confidence == "high"


def test_health_values_are_not_household_cash():
    _, matcher = make_matcher()
    result = matcher.match(UserProfile(**FAMILY))
    for p in result.matched_programs:
        record = next(r for r in PROGRAMS if r.program_id == p.program_id)
        if record.category == "health":
            assert p.monthly_value_usd == 0
    # Totals only count real household dollars.
    assert result.total_estimated_monthly_value == sum(
        p.monthly_value_usd for p in result.matched_programs)


def test_high_income_excludes_income_tested_programs():
    _, matcher = make_matcher(annual_income=200000, household_size=1,
                            has_children=False, children_ages=[])
    result = matcher.match(UserProfile(**{**FAMILY, "annual_income": 200000,
                                          "household_size": 1, "has_children": False,
                                          "children_ages": []}))
    assert result.program_count == 0


def test_pregnant_non_citizen_gets_emergency_medicaid_and_wic():
    profile = UserProfile(**{**FAMILY, "household_size": 2, "annual_income": 20000,
                             "has_children": False, "children_ages": [],
                             "is_pregnant": True, "citizenship": "not_citizen"})
    _, matcher = make_matcher()
    result = matcher.match(profile)
    ids = matched_ids(result)
    assert "emergency_medicaid_tx" in ids
    assert "wic_federal" in ids
    assert "chip_perinatal_tx" in ids  # citizenship not required
    # Programs that require citizenship are capped at low, not hidden.
    by_id = {p.program_id: p for p in result.matched_programs}
    assert by_id["snap_federal"].confidence == "low"
    assert "citizen" not in by_id["snap_federal"].reason or "immigration" in by_id["snap_federal"].reason


def test_citizen_never_gets_emergency_medicaid():
    _, matcher = make_matcher(is_pregnant=True)
    result = matcher.match(UserProfile(**{**FAMILY, "is_pregnant": True}))
    assert "emergency_medicaid_tx" not in matched_ids(result)


def test_unemployed_worker_matches_unemployment():
    _, matcher = make_matcher(employment_status="recently_unemployed")
    result = matcher.match(UserProfile(**{**FAMILY, "employment_status": "recently_unemployed"}))
    by_id = {p.program_id: p for p in result.matched_programs}
    assert "unemployment_benefits_tx" in by_id
    assert by_id["unemployment_benefits_tx"].confidence == "medium"


def test_disability_matches_ssdi_unless_already_receiving():
    profile = UserProfile(**{**FAMILY, "has_disability": True})
    _, matcher = make_matcher()
    assert "ssdi_federal" in matched_ids(matcher.match(profile))

    profile2 = UserProfile(**{**FAMILY, "has_disability": True,
                              "receiving_disability_benefits": True})
    assert "ssdi_federal" not in matched_ids(matcher.match(profile2))


def test_senior_matches_medicare_extra_help_and_mepd():
    profile = UserProfile(**{**FAMILY, "age": 70, "annual_income": 18000,
                             "household_size": 1, "has_children": False,
                             "children_ages": [], "insurance_status": "medicaid_medicare"})
    _, matcher = make_matcher()
    ids = matched_ids(matcher.match(profile))
    assert "medicare_extra_help_federal" in ids
    assert "medicaid_elderly_disabled_tx" in ids


def test_near_threshold_warning():
    # Household of 1 at ~157% FPL: inside the warning band for SNAP (165) and LIHEAP (150).
    profile = UserProfile(**{**FAMILY, "household_size": 1, "annual_income": 25000,
                             "has_children": False, "children_ages": []})
    _, matcher = make_matcher()
    result = matcher.match(profile)
    assert any("income limit" in w for w in result.warnings)


def test_next_steps_built_from_record_fields():
    _, matcher = make_matcher()
    result = matcher.match(UserProfile(**FAMILY))
    snap = next(p for p in result.matched_programs if p.program_id == "snap_federal")
    assert snap.next_steps[0].url == snap.application_url
    doc_step = next(s for s in snap.next_steps if s.documents)
    assert doc_step.documents


def test_insurance_agent_results_merge_and_dedupe():
    class FakeAgent:
        def run(self, profile, rag_context):
            return InsuranceResult(
                qualifies_for=[
                    MatchedProgram(program="CHIP", confidence="high", reason="dup"),
                    MatchedProgram(program="ACA Marketplace subsidies", confidence="medium",
                                   reason="new program"),
                ],
                near_threshold_warnings=["near a threshold"],
                notes="a note",
            )

    _, matcher = make_matcher()
    matcher.insurance_agent = FakeAgent()
    result = matcher.match(UserProfile(**FAMILY))
    names = [p.program for p in result.matched_programs]
    assert "ACA Marketplace subsidies" in names
    assert "CHIP" not in names  # duplicate of the chip_tx record match
    assert "near a threshold" in result.warnings


def test_broken_agent_degrades_silently():
    class BrokenAgent:
        def run(self, profile, rag_context):
            raise RuntimeError("no api key")

    _, matcher = make_matcher()
    matcher.insurance_agent = BrokenAgent()
    result = matcher.match(UserProfile(**FAMILY))
    assert result.program_count > 0  # deterministic matches still return
    assert not any("Health coverage" in w for w in result.warnings)


def test_insurance_agent_results_dedupe_by_program_id():
    class FakeAgent:
        def run(self, profile, rag_context):
            # The agent names programs as the rules text does, not as the records do.
            return InsuranceResult(qualifies_for=[MatchedProgram(
                program_id="childrens_medicaid_tx", program="Children's Medicaid (TX)",
                confidence="high", reason="dup")])

    _, matcher = make_matcher()
    matcher.insurance_agent = FakeAgent()
    result = matcher.match(UserProfile(**FAMILY))
    ids = [p.program_id for p in result.matched_programs]
    assert ids.count("childrens_medicaid_tx") == 1
    assert "Children's Medicaid (TX)" not in [p.program for p in result.matched_programs]


# ---- 2026-10-17 data expansion: age windows and "or" rules the schema cannot express ----

SINGLE = dict(
    state="TX", household_size=1, annual_income=14000, income_bracket="<15k",
    employment_status="employed", age=40, has_children=False, children_ages=[],
    is_pregnant=False, has_disability=False, insurance_status="uninsured",
    citizenship="citizen",
)


def ids_for(base, **overrides):
    profile = UserProfile(**{**base, **overrides})
    return matched_ids(EligibilityMatcher(programs=PROGRAMS).match(profile))


def test_child_age_programs_need_a_child_in_range():
    kid = dict(FAMILY, annual_income=15000, household_size=3, children_ages=[4])
    assert {"head_start_federal", "texas_prekindergarten_tx"} <= ids_for(kid)
    assert "early_head_start_federal" not in ids_for(kid)
    assert "school_breakfast_federal" not in ids_for(kid)
    assert "early_head_start_federal" in ids_for(kid, children_ages=[1])
    assert {"school_breakfast_federal", "summer_meals_federal"} <= ids_for(kid, children_ages=[9])
    assert "head_start_federal" not in ids_for(kid, children_ages=[9])
    assert "early_head_start_federal" in ids_for(SINGLE, is_pregnant=True)


def test_medicare_and_ssi_need_age_or_disability():
    assert not {"medicare_federal", "ssi_federal", "medicare_savings_programs_tx"} & ids_for(SINGLE)
    senior = ids_for(SINGLE, age=70, annual_income=10000, insurance_status="medicaid_medicare")
    assert {"medicare_federal", "ssi_federal", "medicare_savings_programs_tx", "social_security_retirement_federal"} <= senior
    disabled = ids_for(SINGLE, age=45, annual_income=10000, has_disability=True)
    assert {"ssi_federal", "medicare_savings_programs_tx"} <= disabled
    assert "medicare_federal" not in disabled  # Medicare needs 65 or disability benefits
    assert "medicare_federal" in ids_for(SINGLE, age=45, has_disability=True, receiving_disability_benefits=True)


def test_work_and_age_window_programs():
    assert "eitc_federal" in ids_for(SINGLE)
    assert "eitc_federal" not in ids_for(SINGLE, employment_status="unemployed")
    assert "job_corps_federal" in ids_for(SINGLE, age=20)
    assert "job_corps_federal" not in ids_for(SINGLE, age=30)
    assert "ticket_to_work_federal" in ids_for(SINGLE, age=40, has_disability=True, receiving_disability_benefits=True)
    assert "ticket_to_work_federal" not in ids_for(SINGLE, age=40)
    assert "ticket_to_work_federal" not in ids_for(SINGLE, age=66, has_disability=True, receiving_disability_benefits=True)
    assert "family_planning_program_tx" in ids_for(SINGLE, age=30)
    assert "family_planning_program_tx" not in ids_for(SINGLE, age=70)


def test_counseling_programs_follow_age_and_disability_benefits():
    assert "texas_benefits_counseling_tx" in ids_for(SINGLE, age=61, annual_income=10000)
    assert "texas_benefits_counseling_tx" not in ids_for(SINGLE, age=45)
    both = ids_for(SINGLE, age=45, has_disability=True, receiving_disability_benefits=True)
    assert {"work_incentives_planning_federal", "texas_benefits_counseling_tx"} <= both
    assert "work_incentives_planning_federal" not in ids_for(SINGLE, age=45, has_disability=True)


def test_2026_10_17_second_batch_rules():
    kid = dict(FAMILY, annual_income=15000, household_size=3, children_ages=[8], insurance_status="uninsured")
    got = ids_for(kid)
    assert {"national_school_lunch_federal", "texas_vaccines_for_children_tx", "lifeline_federal"} <= got
    assert "texas_vaccines_for_children_tx" not in ids_for(kid, insurance_status="employer")
    assert "child_dependent_care_credit_federal" in got and "child_dependent_care_credit_federal" not in ids_for(kid, employment_status="unemployed")
    assert "credit_for_other_dependents_federal" not in got
    assert "credit_for_other_dependents_federal" in ids_for(kid, children_ages=[17])
    assert "national_school_lunch_federal" not in ids_for(kid, children_ages=[2])
    assert "csfp_federal" in ids_for(SINGLE, age=65, annual_income=15000)
    assert "csfp_federal" not in ids_for(SINGLE, age=50, annual_income=15000)
    assert "csfp_federal" not in ids_for(SINGLE, age=65, annual_income=40000)
