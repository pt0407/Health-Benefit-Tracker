import json
from functools import lru_cache

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response

from agents.ask_agent import AskAgent, AskAgentError
from agents.insurance_agent import InsuranceAgent, InsuranceAgentError
from agents.rate_limit import RateLimiter, client_ip
from config import PROGRAMS_DIR
from export.pdf_export import render_worksheet_pdf
from matching.eligibility_matcher import EligibilityMatcher
from matching.income_scenarios import build_income_scenarios
from models.ask import AskRequest, AskResponse
from models.income_scenarios import IncomeScenariosResponse
from models.match_result import InsuranceResult, MatchResponse
from models.program import Program
from models.user_profile import UserProfile
from rag.rag_engine import BenefitsRAG, IndexNotBuiltError

router = APIRouter()


def load_programs() -> list[Program]:
    programs: list[Program] = []
    for path in sorted(PROGRAMS_DIR.glob("*.json")):
        programs.extend(Program(**p) for p in json.loads(path.read_text()))
    return programs


@lru_cache
def get_rag() -> BenefitsRAG:
    return BenefitsRAG()


@lru_cache
def get_insurance_agent() -> InsuranceAgent:
    return InsuranceAgent()


@lru_cache
def get_matcher() -> EligibilityMatcher:
    # The insurance agent may be an unimplemented stub or unconstructable
    # without ANTHROPIC_API_KEY; the matcher degrades gracefully either way.
    try:
        agent = get_insurance_agent()
    except Exception:
        agent = None
    return EligibilityMatcher(
        rag_engine=get_rag(),
        insurance_agent=agent,
        programs=load_programs(),
    )


@router.post("/match", response_model=MatchResponse)
def match(profile: UserProfile,
          matcher: EligibilityMatcher = Depends(get_matcher)) -> MatchResponse:
    return matcher.match(profile)


@router.post("/income-scenarios", response_model=IncomeScenariosResponse)
def income_scenarios(profile: UserProfile) -> IncomeScenariosResponse:
    """What if the household's income changed? Rules-only matcher over an income grid."""
    return build_income_scenarios(profile, load_programs())


@router.get("/programs", response_model=list[Program])
def list_programs() -> list[Program]:
    return load_programs()


@router.get("/programs/{program_id}", response_model=Program)
def get_program(program_id: str) -> Program:
    for program in load_programs():
        if program.program_id == program_id:
            return program
    raise HTTPException(status_code=404, detail="Program not found")


# Far more than the catalog holds; keeps the public endpoint from rendering huge PDFs.
MAX_EXPORT_PROGRAMS = 100


@router.post("/export/pdf")
def export_pdf(profile: UserProfile = Body(...),
               result: MatchResponse = Body(...)) -> Response:
    if len(result.matched_programs) > MAX_EXPORT_PROGRAMS:
        raise HTTPException(status_code=413, detail="Too many programs to export")
    pdf = render_worksheet_pdf(profile, result)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="civis-worksheet.pdf"'},
    )


@lru_cache
def get_ask_agent() -> AskAgent:
    return AskAgent()


# Every question spends API credit: 10 per person per 10 minutes, 300 an hour overall.
ask_limiter = RateLimiter(per_client=10, client_window_s=600, total=300, total_window_s=3600)


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request, agent: AskAgent = Depends(get_ask_agent)) -> AskResponse:
    """Ask Civis: answer a benefits question from the program records only."""
    if not ask_limiter.allow(client_ip(request.headers, request.client.host if request.client else "?")):
        raise HTTPException(status_code=429, detail="Too many questions right now. Please wait a few minutes.")
    try:
        return agent.run(body)
    except IndexNotBuiltError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except AskAgentError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/insurance-check", response_model=InsuranceResult)
def insurance_check(
    profile: UserProfile,
    agent: InsuranceAgent = Depends(get_insurance_agent),
    rag: BenefitsRAG = Depends(get_rag),
) -> InsuranceResult:
    try:
        rag_context = rag.retrieve_insurance_context(profile)
        return agent.run(profile, rag_context)
    except IndexNotBuiltError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except InsuranceAgentError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
