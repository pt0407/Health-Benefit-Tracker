"""Run the insurance agent against the real Claude API with test profiles.

Usage (from backend/, with ANTHROPIC_API_KEY in backend/.env):
    python -m agents.run_insurance_profiles             # live
    python -m agents.run_insurance_profiles --dry-run   # no API calls
"""

import sys

from agents.insurance_agent import InsuranceAgent, compute_facts
from models.user_profile import UserProfile

BASE = dict(state="TX", is_pregnant=False, has_disability=False,
            citizenship="citizen", has_children=False, children_ages=[])

# (name, profile, programs we expect to see)
CASES = [
    ("Single parent, 2 kids, ~120% FPL",
     UserProfile(**{**BASE, "household_size": 3, "annual_income": 32000, "employment_status": "employed",
                    "age": 34, "has_children": True, "children_ages": [4, 9], "insurance_status": "uninsured"}),
     "Children's Medicaid (both kids); ACA credits for parent"),
    ("Single adult in coverage gap, ~60% FPL",
     UserProfile(**{**BASE, "household_size": 1, "annual_income": 9500, "employment_status": "unemployed",
                    "age": 42, "insurance_status": "uninsured"}),
     "Coverage gap explained in notes; community health centers"),
    ("Pregnant, couple, ~190% FPL (near 198%)",
     UserProfile(**{**BASE, "household_size": 2, "annual_income": 40000, "employment_status": "employed",
                    "age": 27, "is_pregnant": True, "insurance_status": "uninsured"}),
     "Medicaid for Pregnant Women; near-threshold warning"),
    ("Family of 4, kids 7 & 12, ~170% FPL",
     UserProfile(**{**BASE, "household_size": 4, "annual_income": 55000, "employment_status": "self_employed",
                    "age": 45, "has_children": True, "children_ages": [7, 12], "insurance_status": "uninsured"}),
     "CHIP for kids; ACA credits for parents"),
    ("Senior 67, disabled, low income",
     UserProfile(**{**BASE, "household_size": 1, "annual_income": 11000, "employment_status": "unemployed",
                    "age": 67, "has_disability": True, "receiving_disability_benefits": True,
                    "insurance_status": "medicaid_medicare"}),
     "Medicare; MSP/Extra Help; Medicaid for Elderly & Disabled (medium)"),
]


def main():
    dry = "--dry-run" in sys.argv
    agent = None if dry else InsuranceAgent()
    for name, profile, expected in CASES:
        facts = compute_facts(profile)
        print(f"\n=== {name} ===  ({facts['household_income_pct_fpl']}% FPL)")
        print(f"expected: {expected}")
        near = [t["threshold"] for t in facts["thresholds"] if t["near"]]
        print(f"near thresholds: {near or 'none'}")
        if dry:
            continue
        result = agent.run(profile)
        for p in result.qualifies_for:
            print(f"  - [{p.confidence}] {p.program}: {p.reason}")
        for w in result.near_threshold_warnings:
            print(f"  ! {w}")
        if result.notes:
            print(f"  notes: {result.notes}")


if __name__ == "__main__":
    main()
