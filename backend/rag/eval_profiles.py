"""Named retrieval profiles and expectations (Appendix C4), as data.

Used by data/scripts/check_retrieval.py and backend/tests/test_retrieval_quality.py.
Expectations are about which programs surface, never exact scores or chunk text.
"""

from dataclasses import dataclass

from rag.rag_engine import DEFAULT_K

BASE = dict(state="TX", citizenship="citizen", is_pregnant=False, has_disability=False,
            has_children=False, children_ages=[])


@dataclass(frozen=True)
class EvalProfile:
    name: str
    profile: dict
    must_include: tuple
    must_not_include: tuple = ()


def _p(**overrides) -> dict:
    return {**BASE, **overrides}


EVAL_PROFILES = [
    EvalProfile(
        "tx_family_of_4_uninsured",
        _p(household_size=4, annual_income=32000, employment_status="employed", age=34,
           has_children=True, children_ages=[6, 8], insurance_status="uninsured"),
        ("snap_federal", "chip_tx", "childrens_medicaid_tx", "liheap_federal"),
        ("medicare_extra_help_federal",),
    ),
    EvalProfile(
        "pregnant_low_income",
        _p(household_size=2, annual_income=22000, employment_status="employed", age=27,
           is_pregnant=True, insurance_status="uninsured"),
        ("wic_federal", "chip_perinatal_tx", "medicaid_pregnant_women_tx"),
        ("medicare_extra_help_federal",),
    ),
    EvalProfile(
        "senior_67",
        _p(household_size=1, annual_income=16000, employment_status="unemployed", age=67,
           insurance_status="medicaid_medicare"),
        ("medicare_extra_help_federal", "medicaid_elderly_disabled_tx"),
        ("chip_perinatal_tx", "medicaid_pregnant_women_tx", "wic_federal"),
    ),
    EvalProfile(
        "recently_unemployed_single",
        _p(household_size=1, annual_income=12000, employment_status="recently_unemployed", age=30,
           insurance_status="uninsured"),
        ("unemployment_benefits_tx", "snap_federal"),
    ),
    EvalProfile(
        "disabled_adult_50",
        _p(household_size=1, annual_income=13000, employment_status="unemployed", age=50,
           has_disability=True, insurance_status="uninsured"),
        ("ssdi_federal", "medicaid_elderly_disabled_tx"),
    ),
    EvalProfile(
        "pregnant_not_citizen",
        _p(household_size=2, annual_income=30000, employment_status="employed", age=25,
           is_pregnant=True, citizenship="not_citizen", insurance_status="uninsured"),
        ("chip_perinatal_tx", "emergency_medicaid_tx"),
    ),
    EvalProfile(
        "parent_with_toddler",
        _p(household_size=3, annual_income=18000, employment_status="employed", age=29,
           has_children=True, children_ages=[2], insurance_status="uninsured"),
        ("wic_federal", "childrens_medicaid_tx", "tanf_tx", "snap_federal"),
    ),
]


def evaluate(rag, ev: EvalProfile, k: int = DEFAULT_K):
    """Return (ok, missing, unexpected, ids_in_rank_order)."""
    ids = []
    for chunk in rag.retrieve(ev.profile, k=k):
        if chunk.program_id not in ids:
            ids.append(chunk.program_id)
    missing = [i for i in ev.must_include if i not in ids]
    unexpected = [i for i in ev.must_not_include if i in ids]
    return (not missing and not unexpected), missing, unexpected, ids
