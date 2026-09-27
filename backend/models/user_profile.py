"""Quiz output sent by the frontend to POST /api/match. SHARED CONTRACT."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

EmploymentStatus = Literal["employed", "unemployed", "self_employed", "recently_unemployed"]
InsuranceStatus = Literal["uninsured", "employer", "marketplace", "medicaid_medicare", "other"]
# "citizen" means US citizen OR legal permanent resident (quiz Q10 "Yes").
Citizenship = Literal["citizen", "not_citizen", "prefer_not_to_say"]
IncomeBracket = Literal["<15k", "15-30k", "30-50k", "50-75k", "75k+"]


class UserProfile(BaseModel):
    state: str = Field("TX", min_length=2, max_length=2, description="Two-letter state code")
    household_size: int = Field(..., ge=1, le=20)
    annual_income: int = Field(..., ge=0, description="Approximate annual household income, USD")
    income_bracket: Optional[IncomeBracket] = None
    employment_status: EmploymentStatus
    age: int = Field(..., ge=0, le=120)
    has_children: bool
    children_ages: list[int] = Field(default_factory=list)
    is_pregnant: bool
    has_disability: bool
    receiving_disability_benefits: Optional[bool] = None
    insurance_status: InsuranceStatus
    citizenship: Citizenship
