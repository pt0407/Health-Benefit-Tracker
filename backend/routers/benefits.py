import json
from functools import lru_cache

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from agents.insurance_agent import InsuranceAgent, InsuranceAgentError
from config import PROGRAMS_DIR
from export.pdf_export import render_worksheet_pdf
from matching.eligibility_matcher import EligibilityMatcher
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
