"""Income what-if: re-run the deterministic matcher at a grid of incomes.

Powers the "What if your income changes?" slider. Only the hard-rule pass runs
(no insurance agent, no API calls), so a full grid takes milliseconds and costs
nothing. Health coverage comes from the program records alone here.
"""

import math

from matching.eligibility_matcher import EligibilityMatcher, fpl_for_household
from models.income_scenarios import (IncomeScenario, IncomeScenariosResponse, ScenarioMatch,
                                     ScenarioProgram)
from models.program import Program
from models.user_profile import UserProfile

MAX_POINTS = 100
MIN_STEP_USD = 500
# Show up to 4x the poverty line (where most limits end), and well past the
# household's own income when it is already higher.
FPL_MULTIPLE = 4
INCOME_MULTIPLE = 1.5


def income_grid(current: int, fpl: int) -> list[int]:
    top = max(FPL_MULTIPLE * fpl, math.ceil(current * INCOME_MULTIPLE))
    step = max(MIN_STEP_USD, math.ceil(top / MAX_POINTS / MIN_STEP_USD) * MIN_STEP_USD)
    top = math.ceil(top / step) * step
    return sorted(set(range(0, top + 1, step)) | {current})


def build_income_scenarios(profile: UserProfile, programs: list[Program]) -> IncomeScenariosResponse:
    fpl = fpl_for_household(profile.household_size)
    matcher = EligibilityMatcher(insurance_agent=None, programs=programs)
    seen: dict[str, ScenarioProgram] = {}
    scenarios = []
    for income in income_grid(profile.annual_income, fpl):
        result = matcher.match(profile.model_copy(update={"annual_income": income}))
        matches = []
        for m in result.matched_programs:
            if not m.program_id:
                continue
            seen.setdefault(m.program_id, ScenarioProgram(
                program_id=m.program_id, program=m.program, monthly_value_usd=m.monthly_value_usd))
            matches.append(ScenarioMatch(program_id=m.program_id, confidence=m.confidence))
        scenarios.append(IncomeScenario(
            annual_income=income,
            pct_fpl=round(income / fpl * 100, 1),
            program_count=len(matches),
            total_estimated_monthly_value=round(result.total_estimated_monthly_value, 2),
            matches=matches,
        ))
    categories = {p.program_id: p.category for p in programs}
    for sp in seen.values():
        sp.category = categories.get(sp.program_id)
    return IncomeScenariosResponse(
        federal_poverty_level_usd=fpl,
        current_annual_income=profile.annual_income,
        programs=list(seen.values()),
        scenarios=scenarios,
    )
