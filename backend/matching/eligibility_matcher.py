"""Component 5 — Eligibility Matching Engine. Owner: Person 1.

See docs/BUILD_PLAN.md §3 Component 5 for the two-pass design
(deterministic hard rules, then LLM-grounded explanations).

This implementation runs the deterministic pass over the program records in
data/programs/*.json — never hard-coded thresholds — and merges the insurance
agent's health-coverage results on top. Explanations are generated from the
record fields, so nothing here invents eligibility rules.

Record semantics (see CLAUDE.md "Person 2 data and RAG guidance"):
- A null income_limit_pct_fpl means "no income test for this program".
- For banded programs the stored limit is the HIGHEST band, so passing it is
  necessary but not sufficient — those matches stay at "medium" confidence.
- Health-category values are government spending per enrollee, not household
  cash, so matched health programs report monthly_value_usd = 0 and do not
  count toward the value totals.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from models.match_result import ActionStep, MatchedProgram, MatchResponse
from models.program import Program
from models.user_profile import UserProfile

# HHS 2026 poverty guidelines, 48 contiguous states + DC (Texas).
# Source: https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
FEDERAL_POVERTY_LEVELS_2026 = {
    1: 15960, 2: 21640, 3: 27320, 4: 33000,
    5: 38680, 6: 44360, 7: 50040, 8: 55720,
}
_EXTRA_PERSON_ADD = 5680

# How close (in % FPL points) income must be to a limit to warn about a cliff.
NEAR_THRESHOLD_PCT = 10

# A record whose description names more than one income figure is banded: the
# stored income_limit_pct_fpl is only the top band.
_PCT_FIGURE = re.compile(r"\d+(?:\.\d+)?\s*%")
_DOLLAR_TESTED = re.compile(r"income is tested in dollars|in dollars", re.IGNORECASE)


def fpl_for_household(size: int) -> int:
    if size <= 8:
        return FEDERAL_POVERTY_LEVELS_2026[size]
    return FEDERAL_POVERTY_LEVELS_2026[8] + _EXTRA_PERSON_ADD * (size - 8)


def _is_banded(program: Program) -> bool:
    """True when the stored income limit is the top of several bands."""
    return len(_PCT_FIGURE.findall(program.description)) > 1


def _is_dollar_tested(program: Program) -> bool:
    return bool(_DOLLAR_TESTED.search(program.description))


def _household_phrase(profile: UserProfile) -> str:
    n = len(profile.children_ages) or (1 if profile.has_children else 0)
    parts = [f"a household of {profile.household_size}"]
    if n == 1:
        parts.append("your child")
    elif n > 1:
        parts.append(f"your {n} children")
    if profile.is_pregnant:
        parts.append("you during pregnancy")
    return ", ".join(parts)


class EligibilityMatcher:
    """Deterministic matcher over the program records, plus the insurance agent.

    rag_engine may be a BenefitsRAG; if its index is not built the matcher
    still works — RAG only supplies the insurance agent's context.
    insurance_agent may be None when no ANTHROPIC_API_KEY is configured.
    """

    def __init__(self, rag_engine=None, insurance_agent=None,
                 programs: Optional[list[Program]] = None):
        from rag.store import load_programs

        self.rag = rag_engine
        self.insurance_agent = insurance_agent
        self.programs = programs if programs is not None else load_programs()

    def match(self, profile: UserProfile) -> MatchResponse:
        fpl = fpl_for_household(profile.household_size)
        pct_fpl = profile.annual_income / fpl * 100 if fpl else 0.0

        matches: list[MatchedProgram] = []
        warnings: list[str] = []
        for program in self.programs:
            matched = self._check_program(program, profile, pct_fpl)
            if matched is None:
                continue
            matches.append(matched)
            warning = self._near_threshold_warning(program, profile, pct_fpl, fpl)
            if warning:
                warnings.append(warning)

        insurance_warnings, insurance_matches = self._run_insurance_agent(profile)
        warnings.extend(insurance_warnings)
        matched_ids = {m.program_id for m in matches if m.program_id}
        matched_names = {m.program.lower() for m in matches}
        for m in insurance_matches:
            # Skip programs already matched from the records. The agent names
            # programs differently ("CHIP (TX)"), so compare ids first.
            if m.program_id and m.program_id in matched_ids:
                continue
            if not any(m.program.lower() in name or name in m.program.lower()
                       for name in matched_names):
                matches.append(m)

        # Rank by household value first, then name for stability.
        matches.sort(key=lambda m: (-m.monthly_value_usd, m.program))
        monthly_total = sum(m.monthly_value_usd for m in matches)
        return MatchResponse(
            matched_programs=matches,
            total_estimated_monthly_value=monthly_total,
            total_estimated_annual_value=monthly_total * 12,
            program_count=len(matches),
            warnings=warnings,
            generated_at=datetime.now(timezone.utc),
        )

    # -- hard rules ---------------------------------------------------------

    def _check_program(self, program: Program, profile: UserProfile,
                       pct_fpl: float) -> Optional[MatchedProgram]:
        e = program.eligibility

        if e.requires_pregnancy and not profile.is_pregnant:
            return None
        if e.requires_children and not (profile.has_children or profile.children_ages):
            return None
        if e.requires_disability and not (
                profile.has_disability or profile.receiving_disability_benefits):
            return None
        if e.age_max is not None and e.requires_children and profile.children_ages:
            # The age limit applies to the children, not the applicant.
            if all(age > e.age_max for age in profile.children_ages):
                return None
        if e.age_min is not None and profile.age < e.age_min:
            return None

        applies, note = self._extra_conditions(program.program_id, profile)
        if not applies:
            return None

        limit = e.income_limit_pct_fpl
        if limit is not None and pct_fpl > limit:
            return None

        confidence = "high"
        if _is_banded(program) or _is_dollar_tested(program):
            confidence = "medium"  # income fits the top band; exact band is member-specific
        if program.category in {"employment", "disability"}:
            confidence = "medium"  # depends on facts the quiz doesn't collect (work history, separation)
        if profile.citizenship == "prefer_not_to_say" and e.citizenship_required:
            confidence = "medium"
        if profile.citizenship == "not_citizen" and e.citizenship_required:
            confidence = "low"  # depends on immigration status the quiz can't verify
        if program.program_id == "unemployment_benefits_tx" \
                and profile.employment_status == "unemployed":
            confidence = "low"  # separation reason unknown

        reason = self._reason(program, profile, pct_fpl, limit, note, confidence)
        return MatchedProgram(
            program_id=program.program_id,
            program=program.name,
            confidence=confidence,
            reason=reason,
            # Health coverage is per-enrollee spending, not household cash.
            monthly_value_usd=0 if program.category == "health"
            else (program.estimated_monthly_value_usd or 0),
            application_url=program.application_url,
            next_step=f"Apply at {program.application_url}",
            next_steps=self._next_steps(program),
            processing_time=(f"Up to {program.processing_time_days} days"
                             if program.processing_time_days else "Varies"),
            tip="Apply even if you're unsure. The agency will verify your eligibility.",
            source=program.source,
        )

    def _extra_conditions(self, program_id: str, profile: UserProfile) -> tuple[bool, str]:
        """Conditions the schema can't express, keyed by program. Returns
        (applies, reason_note)."""
        if program_id == "medicaid_federal":
            # Texas did not expand Medicaid; adults without kids, pregnancy,
            # disability or age 65+ don't qualify regardless of income.
            ok = (profile.has_children or profile.children_ages or profile.is_pregnant
                  or profile.has_disability or profile.receiving_disability_benefits
                  or profile.age >= 65)
            return ok, "which household members it covers depends on their situation"
        if program_id == "wic_federal":
            ok = profile.is_pregnant or any(a < 5 for a in profile.children_ages)
            return ok, "it covers pregnant women and children under 5"
        if program_id == "medicare_extra_help_federal":
            ok = (profile.age >= 65 or profile.has_disability
                  or profile.receiving_disability_benefits
                  or profile.insurance_status == "medicaid_medicare")
            return ok, "you need Medicare Part A or B to use it"
        if program_id == "emergency_medicaid_tx":
            if profile.citizenship == "citizen":
                return False, ""
            # For Texans who would qualify for Medicaid except for immigration
            # status: pregnant women, children, parents/caretakers, elderly or
            # disabled adults.
            ok = (profile.is_pregnant or profile.has_children or profile.children_ages
                  or profile.age >= 65 or profile.has_disability
                  or profile.receiving_disability_benefits)
            return ok, "it is for people who don't meet regular Medicaid's immigration rules"
        if program_id == "medicaid_elderly_disabled_tx":
            ok = (profile.age >= 65 or profile.has_disability
                  or profile.receiving_disability_benefits)
            return ok, "it covers seniors 65+ and people with disabilities"
        if program_id == "ssdi_federal":
            if profile.receiving_disability_benefits:
                return False, ""  # already receiving disability benefits
            return True, "it also requires enough past work history"
        if program_id == "unemployment_benefits_tx":
            ok = profile.employment_status in {"recently_unemployed", "unemployed"}
            return ok, "it also requires enough past Texas wages and a qualifying job loss"
        return self._extra_conditions_2(program_id, profile)

    def _extra_conditions_2(self, program_id: str, profile: UserProfile) -> tuple[bool, str]:
        """Age windows and "or" rules for the programs added in the 2026-10-17 data expansion."""
        ages = profile.children_ages
        disabled = bool(profile.has_disability or profile.receiving_disability_benefits)
        if program_id == "head_start_federal":
            return any(3 <= a <= 5 for a in ages), "Head Start Preschool serves mainly 3- and 4-year-olds"
        if program_id == "early_head_start_federal":
            return profile.is_pregnant or any(a < 3 for a in ages), "it serves pregnant women and children under 3"
        if program_id == "school_breakfast_federal":
            return any(5 <= a <= 18 for a in ages), "it serves children at participating schools"
        if program_id == "texas_prekindergarten_tx":
            return any(3 <= a <= 4 for a in ages), "the child must be 4 by September 1, or 3 where a district offers it"
        if program_id == "medicare_federal":
            ok = profile.age >= 65 or bool(profile.receiving_disability_benefits)
            return ok, "you qualify at 65 or with Social Security Disability benefits"
        if program_id == "ssi_federal":
            return profile.age >= 65 or disabled, "it is for people who are 65 or older, blind or disabled"
        if program_id == "medicare_savings_programs_tx":
            ok = profile.age >= 65 or disabled or profile.insurance_status == "medicaid_medicare"
            return ok, "you must be entitled to Medicare Part A or Part B-ID"
        if program_id == "eitc_federal":
            return profile.employment_status in {"employed", "self_employed"}, "you need earned income from work"
        if program_id == "job_corps_federal":
            return 16 <= profile.age <= 24, "it is for ages 16 to 24"
        if program_id == "ticket_to_work_federal":
            ok = bool(profile.receiving_disability_benefits) and 18 <= profile.age <= 64
            return ok, "it is for ages 18 to 64 who get SSDI or SSI"
        if program_id == "family_planning_program_tx":
            return profile.age <= 64, "it is for people 64 or younger"
        if program_id == "national_school_lunch_federal":
            return any(5 <= a <= 18 for a in ages), "it serves children at participating schools"
        if program_id == "child_dependent_care_credit_federal":
            ok = profile.employment_status in {"employed", "self_employed"} and any(a <= 12 for a in ages)
            return ok, "you need work-related child care costs for a child under 13"
        if program_id == "credit_for_other_dependents_federal":
            return any(a >= 17 for a in ages), "it is for dependents who do not qualify for the Child Tax Credit, such as a child 17 or older"
        if program_id == "texas_vaccines_for_children_tx":
            ok = any(a <= 18 for a in ages) and profile.insurance_status in {"uninsured", "medicaid_medicare"}
            return ok, "it covers children who are uninsured or on Medicaid or CHIP, and some who are underinsured"
        if program_id == "work_incentives_planning_federal":
            return bool(profile.receiving_disability_benefits), "it counsels people who get Social Security disability benefits"
        if program_id == "texas_benefits_counseling_tx":
            ok = profile.age >= 60 or bool(profile.receiving_disability_benefits)
            return ok, "it is for people 60 or older and Medicare-eligible people with disabilities"
        return True, ""

    def _reason(self, program: Program, profile: UserProfile, pct_fpl: float,
                limit: Optional[float], note: str, confidence: str) -> str:
        who = _household_phrase(profile)
        parts = []
        if limit is None:
            parts.append(f"{program.name} has no household income limit.")
        elif _is_dollar_tested(program):
            parts.append(
                f"{program.name} tests income in dollars, not a percent of the "
                "poverty level. The agency checks your exact monthly income.")
        elif _is_banded(program):
            parts.append(
                f"Your income (~{pct_fpl:.0f}% of the federal poverty level for "
                f"{who}) fits within {program.name}'s published range; the exact "
                "limit depends on each family member's situation.")
        else:
            parts.append(
                f"Your income (~{pct_fpl:.0f}% of the federal poverty level for "
                f"{who}) is below {program.name}'s {limit:.0f}% limit.")
        if note:
            parts.append(f"Note: {note}.")
        if confidence == "low" and profile.citizenship == "not_citizen":
            parts.append("Whether you qualify depends on your immigration status.")
        return " ".join(parts)

    def _near_threshold_warning(self, program: Program, profile: UserProfile,
                                pct_fpl: float, fpl: int) -> Optional[str]:
        limit = program.eligibility.income_limit_pct_fpl
        if limit is None or abs(pct_fpl - limit) > NEAR_THRESHOLD_PCT:
            return None
        limit_usd = round(fpl * limit / 100)
        return (f"You're near the {program.name} income limit. If your household "
                f"income rises above about ${limit_usd:,}/year, you may lose eligibility.")

    # -- action steps --------------------------------------------------------

    def _next_steps(self, program: Program) -> list[ActionStep]:
        steps = [ActionStep(
            step=1, action="Apply online", url=program.application_url,
            time_required="20–30 minutes",
        )]
        if program.documents_needed:
            steps.append(ActionStep(
                step=len(steps) + 1,
                action="Gather these documents before you start",
                documents=program.documents_needed,
            ))
        if program.processing_time_days:
            steps.append(ActionStep(
                step=len(steps) + 1,
                action="Wait for the agency's decision",
                note=f"Processing takes up to {program.processing_time_days} days",
            ))
        return steps

    # -- insurance agent -----------------------------------------------------

    def _run_insurance_agent(self, profile: UserProfile) -> tuple[list[str], list[MatchedProgram]]:
        if self.insurance_agent is None:
            return [], []
        rag_context = ""
        if self.rag is not None:
            try:
                rag_context = self.rag.retrieve_insurance_context(profile)
            except Exception:
                # A missing index must not take down the whole match.
                rag_context = ""
        try:
            result = self.insurance_agent.run(profile, rag_context)
        except Exception:
            return [], []
        warnings = list(result.near_threshold_warnings)
        if result.notes:
            warnings.append(f"Health coverage note: {result.notes}")
        return warnings, list(result.qualifies_for)
