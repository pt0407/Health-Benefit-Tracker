"""Component 3 — Insurance Coverage Agent. Owner: Person 4.

Given a quiz profile, decides which health-coverage programs the household
likely qualifies for (Medicaid, CHIP, ACA subsidies, Medicare, TX programs).

Design:
- Arithmetic is done here, deterministically: income as % of FPL and the
  dollar value of every threshold for this household size. The model is
  handed those numbers instead of computing them.
- The model only reasons over the rules text it is given (baseline TX rules
  plus the program records the RAG engine retrieves), and its reply is
  constrained to the InsuranceResult schema via structured outputs.
- Health coverage has no cash value to the household. The dollar figures in
  the records are estimated government spending per enrollee, so
  monthly_value_usd is forced to 0 after parsing.
"""

import json
import re

import anthropic
import pydantic

from agents.insurance_rules import TX_INSURANCE_RULES
from agents.screening import NEAR_THRESHOLD_PCT, identify, screen
from config import CLAUDE_MODEL
from matching.eligibility_matcher import fpl_for_household
from models.match_result import InsuranceResult
from models.user_profile import UserProfile

# False claims the model keeps making despite the prompt. Any sentence that
# matches is removed from the result after parsing.
FALSE_CLAIM_PATTERNS = [
    # Pregnancy is not a Special Enrollment Period trigger; having a baby is.
    re.compile(r"pregnan[^.!?]*special enrollment|special enrollment[^.!?]*pregnan", re.IGNORECASE),
]
_SENTENCE_END = re.compile(r"(?<=[.!?])(\s+)")
_EM_DASH = re.compile(r"\s*\u2014\s*")

# States TX_INSURANCE_RULES covers. Other states get an explanatory note
# instead of a model call.
SUPPORTED_STATES = {"TX"}
UNSUPPORTED_STATE_NOTE = (
    "Civis can only check health coverage for Texas right now, so we "
    "can't tell which programs you qualify for in your state yet. You can "
    "compare Marketplace plans and savings at https://www.healthcare.gov."
)

SYSTEM_PROMPT = """\
You are a benefits navigator specializing in health coverage programs. You \
help families understand which health insurance programs they likely qualify \
for and what to do first.

Use ONLY the eligibility rules in the <rules> block: the baseline Texas rules \
and, after them, official program records retrieved for this household. If a \
retrieved record and the baseline rules disagree, follow the retrieved record. \
Never invent programs, \
income limits, percentages, prices, URLs, phone numbers, helplines, organizations, \
coverage start dates or enrollment rules. This applies to every field, \
including `notes` and `next_step`. Mention only the enrollment periods and \
Special Enrollment Period triggers the rules list, and no other dates. If the rules don't cover a situation, say \
so in `notes` rather than guessing. Use the precomputed numbers in \
<computed_facts>; do not redo the arithmetic.

<computed_facts> also screens the programs for this household. \
`qualifies_for` may list ONLY programs in `programs_to_consider`, and only \
those the rules say this household likely qualifies for. Never list a program \
from `ruled_out`; you may mention one in `notes` using the reason given. Never \
add an entry for a situation such as the coverage gap. If no program applies, \
leave `qualifies_for` empty and explain in `notes`. For each program the household \
likely qualifies for, add one entry:
- `program`: the program name as written in the rules.
- `program_id`: the id in square brackets after "Program:" in the retrieved \
record for this program (e.g. "chip_tx"). Leave it out if no retrieved \
record matches.
- `confidence`: "high" only when the profile clearly meets every stated \
rule. "medium" when a stated rule depends on something the profile doesn't \
include, such as a resource/asset limit (the quiz never asks about savings \
or assets). "low" when it's possible but unlikely. For ACA premium tax \
credits specifically: "medium" if employment_status is "employed" (we don't \
know whether they have an affordable employer plan), otherwise "high" when \
income is 100-400% FPL. An employer plan never affects Medicaid or CHIP \
confidence.
- Citizenship: "not_citizen" means not a U.S. citizen or green-card holder. \
The screening already accounts for it. Programs for children depend on each \
child's own status (children born in the U.S. are citizens). For \
"prefer_not_to_say", programs that require a qualifying status are "medium" \
at most, and say it depends on immigration status. If the household is \
"not_citizen", add a sentence to `notes` that some immigration statuses can \
still qualify for regular Medicaid and CHIP (the rules say a recent law change \
limited which ones), so they can apply and Texas HHSC will check.
- `reason`: one or two plain-English sentences a non-expert can follow. Say \
who in the household it covers (e.g. "your two children"). Count adults as \
household_size minus the number of children; if there are two or more \
adults, don't write as if there is only one.
- `monthly_value_usd`: always 0. Dollar amounts labeled as an estimated or \
monthly value in the records are government spending per enrollee or \
program-wide averages, not money this household receives. Never mention \
them in any field.
- `application_url` and `next_step`: from the rules; `next_step` is the \
single first thing to do.
- `source`: the source named in the rules.

Put a sentence in `near_threshold_warnings` for every threshold listed as \
"near" in <computed_facts>, explaining what would change if income moved \
past it. Use `coverage_gap` in <computed_facts>: if "yes", explain the Texas \
coverage gap in `notes` along with the alternatives the rules list; if it \
names a condition, explain the gap only as applying under that condition; \
if "no", don't mention it. Write to the user as \
"you", for someone who may be stressed about money: clear, kind, no jargon. \
Never use em dashes; use a comma, colon or new sentence instead."""


class InsuranceAgentError(RuntimeError):
    """The agent could not produce a result (API error, refusal, bad output)."""


def compute_facts(profile: UserProfile) -> dict:
    fpl = fpl_for_household(profile.household_size)
    pct_fpl = round(profile.annual_income / fpl * 100, 1)
    sc = screen(profile, pct_fpl)
    thresholds = []
    for name, pct in sc.thresholds.items():
        thresholds.append({
            "threshold": name,
            "pct_fpl": pct,
            "annual_income_limit_usd": round(fpl * pct / 100),
            "household_is_below": pct_fpl <= pct,
            "near": abs(pct_fpl - pct) <= NEAR_THRESHOLD_PCT,
        })
    return {
        "federal_poverty_level_usd": fpl,
        "household_income_pct_fpl": pct_fpl,
        "programs_to_consider": [{"program": p, "why": why} for p, why in sc.consider.items()],
        "ruled_out": [{"program": p, "why": why} for p, why in sc.ruled_out.items()],
        "coverage_gap": sc.coverage_gap,
        "thresholds": thresholds,
    }


class InsuranceAgent:
    def __init__(self, client: anthropic.Anthropic | None = None, model: str = CLAUDE_MODEL):
        self.client = client or anthropic.Anthropic()
        self.model = model

    def build_prompt(self, profile: UserProfile, rag_context: str = "") -> str:
        rules = TX_INSURANCE_RULES
        if rag_context.strip():
            rules += "\nRETRIEVED PROGRAM RECORDS (official sources):\n" + rag_context
        return (
            f"<rules>\n{rules}\n</rules>\n\n"
            f"<user_profile>\n{profile.model_dump_json(indent=2)}\n</user_profile>\n\n"
            f"<computed_facts>\n{json.dumps(compute_facts(profile), indent=2)}\n</computed_facts>\n\n"
            "Which health coverage programs does this household likely qualify for?"
        )

    def run(self, profile: UserProfile, rag_context: str = "") -> InsuranceResult:
        # The rules are Texas-only; don't let the model apply them elsewhere.
        if profile.state.upper() not in SUPPORTED_STATES:
            return InsuranceResult(qualifies_for=[], notes=UNSUPPORTED_STATE_NOTE)
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": self.build_prompt(profile, rag_context)}],
                output_format=InsuranceResult,
            )
        except anthropic.APIError as e:
            raise InsuranceAgentError(f"Claude API error: {e}") from e
        except TypeError as e:
            # With no ANTHROPIC_API_KEY the SDK raises TypeError while building
            # the request, not APIError. Other TypeErrors are real bugs.
            if "authentication" not in str(e):
                raise
            raise InsuranceAgentError("Claude API key is not configured") from e
        except pydantic.ValidationError as e:
            # parse() validates eagerly, so a refusal or truncated reply
            # surfaces here rather than through stop_reason.
            raise InsuranceAgentError("Claude did not return a complete result") from e

        if response.stop_reason == "refusal":
            raise InsuranceAgentError("Claude declined to answer this request")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise InsuranceAgentError(f"Incomplete response (stop_reason={response.stop_reason})")
        result = drop_ruled_out(profile, response.parsed_output)
        return remove_em_dashes(zero_monthly_values(strip_false_claims(result)))


def drop_ruled_out(profile: UserProfile, result: InsuranceResult) -> InsuranceResult:
    """Remove programs the deterministic screen ruled out for this household."""
    facts = compute_facts(profile)
    ruled_out = {r["program"] for r in facts["ruled_out"]}
    kept = [p for p in result.qualifies_for if identify(p.program, p.program_id) not in ruled_out]
    return result.model_copy(update={"qualifies_for": kept})


def zero_monthly_values(result: InsuranceResult) -> InsuranceResult:
    """Health coverage is not cash: never report a dollar value to the household."""
    programs = [p.model_copy(update={"monthly_value_usd": 0}) for p in result.qualifies_for]
    return result.model_copy(update={"qualifies_for": programs})


def _no_em_dash(text: str | None) -> str | None:
    # The prompt forbids em dashes; this catches any the model still writes.
    return _EM_DASH.sub(", ", text) if text else text


def remove_em_dashes(result: InsuranceResult) -> InsuranceResult:
    """Replace em dashes in every user-facing text field with a comma."""
    programs = [
        p.model_copy(update={f: _no_em_dash(getattr(p, f)) for f in ("program", "reason", "next_step", "tip")})
        for p in result.qualifies_for
    ]
    return result.model_copy(update={
        "qualifies_for": programs,
        "near_threshold_warnings": [_no_em_dash(w) for w in result.near_threshold_warnings],
        "notes": _no_em_dash(result.notes),
    })


def _strip_sentences(text: str | None) -> str | None:
    if not text:
        return text
    # Split keeping the whitespace after each sentence so paragraphs survive.
    parts = _SENTENCE_END.split(text)
    sentences, seps = parts[0::2], parts[1::2] + [""]
    kept = [s + sep for s, sep in zip(sentences, seps)
            if not any(p.search(s) for p in FALSE_CLAIM_PATTERNS)]
    return "".join(kept).strip()


def strip_false_claims(result: InsuranceResult) -> InsuranceResult:
    """Drop sentences matching FALSE_CLAIM_PATTERNS from every text field."""
    programs = [
        p.model_copy(update={f: _strip_sentences(getattr(p, f)) for f in ("reason", "next_step", "tip")})
        for p in result.qualifies_for
    ]
    warnings = [w for w in (_strip_sentences(w) for w in result.near_threshold_warnings) if w]
    return result.model_copy(update={
        "qualifies_for": programs,
        "near_threshold_warnings": warnings,
        "notes": _strip_sentences(result.notes),
    })
