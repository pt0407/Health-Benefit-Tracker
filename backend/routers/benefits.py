import json
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from agents.insurance_agent import InsuranceAgent, InsuranceAgentError
from config import FIXTURES_DIR, PROGRAMS_DIR
from models.match_result import InsuranceResult, MatchResponse
from models.program import Program
from models.user_profile import UserProfile

router = APIRouter()


def load_programs() -> list[Program]:
    programs: list[Program] = []
    for path in sorted(PROGRAMS_DIR.glob("*.json")):
        programs.extend(Program(**p) for p in json.loads(path.read_text()))
    return programs


@router.post("/match", response_model=MatchResponse)
def match(profile: UserProfile) -> MatchResponse:
    # TODO(Person 1): replace with EligibilityMatcher once it lands.
    # Returns a fixed sample so the frontend can be built in parallel.
    return MatchResponse(**json.loads((FIXTURES_DIR / "sample_match_response.json").read_text()))


@router.get("/programs", response_model=list[Program])
def list_programs() -> list[Program]:
    return load_programs()


@router.get("/programs/{program_id}", response_model=Program)
def get_program(program_id: str) -> Program:
    for program in load_programs():
        if program.program_id == program_id:
            return program
    raise HTTPException(status_code=404, detail="Program not found")


@lru_cache
def get_insurance_agent() -> InsuranceAgent:
    return InsuranceAgent()


@router.post("/insurance-check", response_model=InsuranceResult)
def insurance_check(
    profile: UserProfile, agent: InsuranceAgent = Depends(get_insurance_agent)
) -> InsuranceResult:
    # TODO(Person 2): pass RAG context once BenefitsRAG is implemented.
    try:
        return agent.run(profile)
    except InsuranceAgentError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
