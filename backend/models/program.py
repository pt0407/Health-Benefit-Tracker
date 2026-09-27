"""Benefit program schema for data/programs/*.json. SHARED CONTRACT."""

from typing import Literal, Optional

from pydantic import BaseModel


class Eligibility(BaseModel):
    income_limit_pct_fpl: Optional[float] = None
    citizenship_required: bool = False
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    requires_children: bool = False
    requires_disability: bool = False
    requires_pregnancy: bool = False


class Program(BaseModel):
    program_id: str
    name: str
    type: Literal["federal", "state", "federal_state"]
    category: str
    description: str
    eligibility: Eligibility
    estimated_monthly_value_usd: Optional[float] = None
    application_url: str
    documents_needed: list[str] = []
    processing_time_days: Optional[int] = None
    source: str
    last_updated: str
