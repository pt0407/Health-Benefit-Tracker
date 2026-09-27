"""Response shapes for POST /api/match and POST /api/insurance-check. SHARED CONTRACT."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

Confidence = Literal["high", "medium", "low"]


class ActionStep(BaseModel):
    step: int
    action: str
    url: Optional[str] = None
    time_required: Optional[str] = None
    documents: Optional[list[str]] = None
    note: Optional[str] = None


class MatchedProgram(BaseModel):
    program_id: Optional[str] = None
    program: str
    confidence: Confidence
    reason: str
    monthly_value_usd: float = 0
    application_url: Optional[str] = None
    next_step: Optional[str] = None
    # Filled in by the Action Plan Generator (Component 6).
    next_steps: list[ActionStep] = []
    processing_time: Optional[str] = None
    tip: Optional[str] = None
    source: Optional[str] = None


class MatchResponse(BaseModel):
    matched_programs: list[MatchedProgram]
    total_estimated_annual_value: float
    total_estimated_monthly_value: float
    program_count: int
    warnings: list[str] = []
    generated_at: datetime


class InsuranceResult(BaseModel):
    qualifies_for: list[MatchedProgram]
    near_threshold_warnings: list[str] = []
    notes: str = ""
