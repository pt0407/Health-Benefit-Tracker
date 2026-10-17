"""Response shape for POST /api/income-scenarios. SHARED CONTRACT.

The "what if my income changes?" view. The request body is a UserProfile; the
deterministic matcher is re-run at a grid of incomes (the insurance agent is
not run, so health results come from the program records only).
"""

from typing import Optional

from pydantic import BaseModel

from models.match_result import Confidence


class ScenarioProgram(BaseModel):
    """A program that fits at one or more incomes on the grid."""
    program_id: str
    program: str
    category: Optional[str] = None
    # Estimated value to the household; 0 for health coverage (not cash).
    monthly_value_usd: float = 0


class ScenarioMatch(BaseModel):
    program_id: str
    confidence: Confidence


class IncomeScenario(BaseModel):
    annual_income: int
    pct_fpl: float
    program_count: int
    total_estimated_monthly_value: float
    matches: list[ScenarioMatch]


class IncomeScenariosResponse(BaseModel):
    federal_poverty_level_usd: int
    current_annual_income: int
    programs: list[ScenarioProgram]   # every program in any scenario, by program_id
    scenarios: list[IncomeScenario]   # ascending by annual_income; includes current income
