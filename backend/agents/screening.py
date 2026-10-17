"""Deterministic pre-screen for the insurance agent.

Decides, from the quiz profile alone, which Texas health programs could apply
to the household, which are ruled out and why, which income thresholds are
worth warning about, and whether the household is in the coverage gap. The
model only explains and ranks what this module allows, and anything it lists
from the ruled-out set is removed after parsing.

Program names match the headings in insurance_rules.TX_INSURANCE_RULES.
"""

import re
from dataclasses import dataclass, field

from models.user_profile import UserProfile

CHILDREN_MEDICAID = "Children's Medicaid (TX)"
CHIP = "CHIP (TX)"
PREGNANT_WOMEN = "Medicaid for Pregnant Women (TX)"
CHIP_PERINATAL = "CHIP Perinatal (TX)"
EMERGENCY = "Emergency Medicaid (TX)"
MEPD = "Medicaid for the Elderly and People with Disabilities (MEPD, TX)"
PARENT_CARETAKER = "Parent and caretaker Medicaid (TX)"
ACA = "ACA Marketplace premium tax credits"
MEDICARE = "Medicare"
EXTRA_HELP = "Medicare Part D Extra Help"

# How an agent result is recognized as one of the programs above: record ids
# first (from the RAG context), then name patterns, checked in this order.
_RECORD_IDS = {
    "childrens_medicaid_tx": CHILDREN_MEDICAID,
    "chip_tx": CHIP,
    "medicaid_pregnant_women_tx": PREGNANT_WOMEN,
    "chip_perinatal_tx": CHIP_PERINATAL,
    "emergency_medicaid_tx": EMERGENCY,
    "medicaid_elderly_disabled_tx": MEPD,
    "medicare_extra_help_federal": EXTRA_HELP,
}
_NAME_PATTERNS = [
    (CHIP_PERINATAL, r"perinatal"),
    (EMERGENCY, r"emergency medicaid"),
    (PREGNANT_WOMEN, r"pregnant women"),
    (MEPD, r"elderly|mepd|people with disabilities"),
    (EXTRA_HELP, r"extra help|part d|low.income subsidy"),
    (MEDICARE, r"medicare"),
    (CHILDREN_MEDICAID, r"children'?s medicaid"),
    (CHIP, r"\bchip\b|children'?s health insurance"),
    (PARENT_CARETAKER, r"parent|caretaker"),
    (ACA, r"marketplace|premium tax credit|\baca\b"),
]

NEAR_THRESHOLD_PCT = 10


@dataclass
class Screen:
    consider: dict[str, str] = field(default_factory=dict)   # program -> why it may apply
    ruled_out: dict[str, str] = field(default_factory=dict)  # program -> why not
    thresholds: dict[str, float] = field(default_factory=dict)  # label -> % FPL
    coverage_gap: str = "no"


def identify(program_name: str, program_id: str | None = None) -> str | None:
    """Map an agent result to one of the screened programs, if possible."""
    if program_id in _RECORD_IDS:
        return _RECORD_IDS[program_id]
    name = program_name.lower()
    for program, pattern in _NAME_PATTERNS:
        if re.search(pattern, name):
            return program
    return None


def screen(profile: UserProfile, pct_fpl: float) -> Screen:
    s = Screen()
    ages = profile.children_ages
    has_kids = profile.has_children or bool(ages)
    citizen = profile.citizenship == "citizen"
    not_citizen = profile.citizenship == "not_citizen"
    disabled = profile.has_disability or bool(profile.receiving_disability_benefits)
    senior = profile.age >= 65
    on_medicare_or_medicaid = profile.insurance_status == "medicaid_medicare"
    status_note = ("it requires U.S. citizenship or a qualified immigration status, "
                   "and you said you are not a citizen or green-card holder")

    # Children: their own citizenship is what counts, and children born in the
    # U.S. are citizens, so these stay open for non-citizen parents.
    if has_kids:
        s.consider[CHILDREN_MEDICAID] = "you have children; the limit depends on each child's age"
        s.consider[CHIP] = "you have children; it covers children above the Children's Medicaid limit"
        if any(a < 1 for a in ages):
            s.thresholds["Children's Medicaid, children under 1"] = 198
        if any(1 <= a <= 5 for a in ages):
            s.thresholds["Children's Medicaid, children 1-5"] = 144
        if any(6 <= a <= 18 for a in ages):
            s.thresholds["Children's Medicaid, children 6-18"] = 133
        s.thresholds["CHIP"] = 201

    if profile.is_pregnant:
        if not_citizen:
            s.ruled_out[PREGNANT_WOMEN] = status_note
        else:
            s.consider[PREGNANT_WOMEN] = "you are pregnant"
            s.thresholds["Medicaid for Pregnant Women"] = 198
        if not citizen or pct_fpl > 198:
            s.consider[CHIP_PERINATAL] = (
                "you are pregnant and cannot get Medicaid because of immigration status"
                if not_citizen else "you are pregnant and your income may be above the Medicaid limit")
            s.thresholds["CHIP Perinatal"] = 202
        else:
            s.ruled_out[CHIP_PERINATAL] = "Medicaid for Pregnant Women covers you at this income instead"

    # Emergency Medicaid: Medicaid rules except immigration status.
    if not citizen and (profile.is_pregnant or has_kids or senior or disabled):
        s.consider[EMERGENCY] = (
            "it pays for emergency care, including labor and delivery, when immigration "
            "status rules out regular Medicaid")
        if profile.is_pregnant:
            s.thresholds["Emergency Medicaid, pregnancy (labor and delivery)"] = 198

    if senior or disabled:
        if not_citizen:
            s.ruled_out[MEPD] = status_note
        else:
            s.consider[MEPD] = "you are 65 or older or have a disability; income is tested in dollars"

    if has_kids and pct_fpl <= 12 and not not_citizen:
        s.consider[PARENT_CARETAKER] = "you are a parent with very low income"

    # Medicare: 65+, or after 24 months of SSDI.
    medicare_route = senior or bool(profile.receiving_disability_benefits)
    if medicare_route and not not_citizen:
        if on_medicare_or_medicaid:
            s.ruled_out[MEDICARE] = "you said you already have Medicare or Medicaid"
        elif senior:
            s.consider[MEDICARE] = "you are 65 or older"
        else:
            s.consider[MEDICARE] = (
                "it starts after 24 months of Social Security Disability (SSDI) benefits; "
                "it depends on whether your disability benefits are SSDI and for how long")
        s.consider[EXTRA_HELP] = "it lowers drug costs for people with Medicare"
        s.thresholds["Medicare Extra Help"] = 150

    if not_citizen:
        s.ruled_out[ACA] = status_note
    elif senior:
        s.ruled_out[ACA] = "people 65 and older use Medicare instead"
    else:
        if 100 <= pct_fpl <= 400:
            s.consider[ACA] = "your income is between 100% and 400% of the poverty level"
        elif pct_fpl > 400:
            s.ruled_out[ACA] = "your income is above 400% of the poverty level"
        else:
            s.ruled_out[ACA] = "your income is below 100% of the poverty level"
        s.thresholds["ACA subsidy floor"] = 100
        s.thresholds["ACA subsidy ceiling"] = 400

    # Coverage gap: an adult under 65 below 100% FPL with no Medicaid route.
    adult = 19 <= profile.age <= 64
    if adult and pct_fpl < 100 and not profile.is_pregnant and not not_citizen:
        parent_route = has_kids and pct_fpl <= 12
        if disabled:
            s.coverage_gap = "only if MEPD and Medicare do not apply"
        elif not parent_route:
            s.coverage_gap = "yes"
    return s
