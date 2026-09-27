"""Component 3 — Insurance Coverage Agent. Owner: Person 4.

See docs/BUILD_PLAN.md §3 Component 3. Use structured outputs rather than
parsing raw text:

    response = client.messages.parse(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        system=...,
        messages=[...],
        output_format=InsuranceResult,
    )
    result = response.parsed_output  # validated InsuranceResult
"""

from models.match_result import InsuranceResult
from models.user_profile import UserProfile


class InsuranceAgent:
    def run(self, profile: UserProfile, rag_context: str) -> InsuranceResult:
        raise NotImplementedError
