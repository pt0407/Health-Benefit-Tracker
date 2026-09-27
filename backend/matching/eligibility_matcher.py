"""Component 5 — Eligibility Matching Engine. Owner: Person 1.

See docs/BUILD_PLAN.md §3 Component 5 for the two-pass design
(deterministic hard rules, then LLM-grounded explanations).
"""

from models.match_result import MatchResponse
from models.user_profile import UserProfile

# HHS 2025 poverty guidelines (48 contiguous states). Each extra person adds $5,500.
# TODO: update to the 2026 guidelines.
FEDERAL_POVERTY_LEVELS_2025 = {
    1: 15650, 2: 21150, 3: 26650, 4: 32150,
    5: 37650, 6: 43150, 7: 48650, 8: 54150,
}


def fpl_for_household(size: int) -> int:
    if size <= 8:
        return FEDERAL_POVERTY_LEVELS_2025[size]
    return FEDERAL_POVERTY_LEVELS_2025[8] + 5500 * (size - 8)


class EligibilityMatcher:
    def __init__(self, rag_engine, insurance_agent):
        self.rag = rag_engine
        self.insurance_agent = insurance_agent

    def match(self, profile: UserProfile) -> MatchResponse:
        raise NotImplementedError
