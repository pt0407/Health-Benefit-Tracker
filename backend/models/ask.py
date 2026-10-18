"""Request and response shapes for POST /api/ask ("Ask Civis"). SHARED CONTRACT.

Questions are answered only from the program records in data/programs, with a
source link for every program the answer relies on.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from models.user_profile import UserProfile

MAX_QUESTION_CHARS = 500
MAX_HISTORY_TURNS = 6


class AskTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=MAX_QUESTION_CHARS)
    # Earlier turns of this conversation, oldest first, so follow-ups make sense.
    history: list[AskTurn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)
    # Optional quiz answers, so "do I qualify?" can be answered for this household.
    profile: Optional[UserProfile] = None


class AskSource(BaseModel):
    program_id: str
    program_name: str
    url: str          # official page the record was built from, or the application page


class AskResponse(BaseModel):
    answer: str
    sources: list[AskSource] = []
    # False when the records don't cover the question; the answer then says so
    # and points to where to ask instead.
    answered_from_records: bool = True
