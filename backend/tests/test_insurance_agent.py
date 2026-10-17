"""Insurance agent tests. The Anthropic client runs for real against a fake
HTTP transport, so request building and structured-output parsing are
exercised without calling the API."""

import json

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from agents.insurance_agent import InsuranceAgent, InsuranceAgentError, compute_facts
from main import app
from models.user_profile import UserProfile
from rag.rag_engine import IndexNotBuiltError
from routers.benefits import get_insurance_agent, get_rag
from tests.test_api import SAMPLE_PROFILE

AGENT_OUTPUT = {
    "qualifies_for": [
        {
            "program": "Children's Medicaid (TX)",
            "confidence": "high",
            "reason": "Your two children (ages 6 and 8) qualify because income is under 133% FPL.",
            "monthly_value_usd": 0,
            "application_url": "https://www.yourtexasbenefits.com",
            "next_step": "Apply for your children at YourTexasBenefits.com",
            "source": "Texas HHSC",
        }
    ],
    "near_threshold_warnings": ["You're just under 100% FPL..."],
    "notes": "As an adult, you fall in the Texas coverage gap.",
}


class FakeRAG:
    def __init__(self, context="Program: CHIP Perinatal [chip_perinatal_tx]", error=None):
        self.context, self.error = context, error

    def retrieve_insurance_context(self, profile):
        if self.error:
            raise self.error
        return self.context


def post_insurance_check(agent, rag=None):
    app.dependency_overrides[get_insurance_agent] = lambda: agent
    app.dependency_overrides[get_rag] = lambda: rag or FakeRAG()
    try:
        return TestClient(app).post("/api/insurance-check", json=SAMPLE_PROFILE)
    finally:
        app.dependency_overrides.clear()


def fake_client(stop_reason="end_turn", text=None, status=200, captured=None):
    def handler(request: httpx2.Request) -> httpx2.Response:
        if captured is not None:
            captured.append(json.loads(request.content))
        if status != 200:
            return httpx2.Response(status, json={"type": "error", "error": {"type": "api_error", "message": "boom"}})
        return httpx2.Response(200, json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "test-model",
            "content": [{"type": "text", "text": text if text is not None else json.dumps(AGENT_OUTPUT)}],
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })

    return anthropic.Anthropic(
        api_key="test", max_retries=0, http_client=httpx2.Client(transport=httpx2.MockTransport(handler))
    )


PROFILE = UserProfile(**SAMPLE_PROFILE)


def test_compute_facts_family_of_four():
    facts = compute_facts(PROFILE)
    assert facts["federal_poverty_level_usd"] == 33000
    assert facts["household_income_pct_fpl"] == 97.0
    by_name = {t["threshold"]: t for t in facts["thresholds"]}
    floor = by_name["ACA subsidy floor"]
    assert floor["annual_income_limit_usd"] == 33000
    assert floor["household_is_below"] and floor["near"]
    assert not by_name["ACA subsidy ceiling"]["near"]


def test_run_parses_structured_output_and_sends_grounding():
    captured = []
    result = InsuranceAgent(client=fake_client(captured=captured), model="test-model").run(PROFILE, "RAG TEXT")

    assert result.qualifies_for[0].program == "Children's Medicaid (TX)"
    assert result.notes.startswith("As an adult")

    body = captured[0]
    prompt = body["messages"][0]["content"]
    assert "TEXAS HEALTH COVERAGE RULES" in prompt
    assert "RAG TEXT" in prompt
    assert '"household_income_pct_fpl": 97.0' in prompt
    assert body["output_config"]["format"]["type"] == "json_schema"


@pytest.mark.parametrize(
    "stop_reason,text",
    [("refusal", ""), ("max_tokens", '{"qualifies_for": ['), ("end_turn", '{"wrong": 1}')],
)
def test_run_raises_on_unusable_output(stop_reason, text):
    agent = InsuranceAgent(client=fake_client(stop_reason=stop_reason, text=text), model="test-model")
    with pytest.raises(InsuranceAgentError):
        agent.run(PROFILE)


def test_run_raises_on_api_error():
    agent = InsuranceAgent(client=fake_client(status=500), model="test-model")
    with pytest.raises(InsuranceAgentError, match="API error"):
        agent.run(PROFILE)


def test_run_strips_pregnancy_sep_claim():
    output = json.loads(json.dumps(AGENT_OUTPUT))
    output["qualifies_for"][0]["next_step"] = (
        "Apply at YourTexasBenefits.com. Being pregnant opens a Special Enrollment Period."
    )
    output["notes"] = "First paragraph.\n\nPregnancy qualifies you for special enrollment. Last sentence."
    result = InsuranceAgent(client=fake_client(text=json.dumps(output)), model="test-model").run(PROFILE)

    assert result.qualifies_for[0].next_step == "Apply at YourTexasBenefits.com."
    assert result.notes == "First paragraph.\n\nLast sentence."


def test_run_skips_model_for_unsupported_state():
    captured = []
    profile = PROFILE.model_copy(update={"state": "CA"})
    result = InsuranceAgent(client=fake_client(captured=captured), model="test-model").run(profile)

    assert captured == []
    assert result.qualifies_for == []
    assert "Texas" in result.notes


def test_insurance_check_endpoint_maps_missing_api_key_to_502(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    client = anthropic.Anthropic(max_retries=0, http_client=httpx2.Client(transport=httpx2.MockTransport(
        lambda request: pytest.fail("request should not be sent without a key"))))
    res = post_insurance_check(InsuranceAgent(client=client, model="test-model"))
    assert res.status_code == 502
    assert "API key" in res.json()["detail"]


def test_insurance_check_endpoint_sends_retrieved_records():
    captured = []
    res = post_insurance_check(
        InsuranceAgent(client=fake_client(captured=captured), model="test-model"),
        FakeRAG(context="Program: CHIP Perinatal [chip_perinatal_tx] RETRIEVED-MARKER"),
    )
    assert res.status_code == 200
    assert res.json()["qualifies_for"][0]["confidence"] == "high"
    prompt = captured[0]["messages"][0]["content"]
    assert "RETRIEVED PROGRAM RECORDS" in prompt
    assert "RETRIEVED-MARKER" in prompt


def test_insurance_check_endpoint_maps_missing_index_to_503():
    agent = InsuranceAgent(client=fake_client(), model="test-model")
    res = post_insurance_check(agent, FakeRAG(error=IndexNotBuiltError("Build it with: python data/scripts/index_to_chromadb.py")))
    assert res.status_code == 503
    assert "index_to_chromadb" in res.json()["detail"]


def test_run_zeroes_monthly_values():
    output = json.loads(json.dumps(AGENT_OUTPUT))
    output["qualifies_for"][0]["monthly_value_usd"] = 308
    agent = InsuranceAgent(client=fake_client(text=json.dumps(output)), model="test-model")
    assert agent.run(PROFILE).qualifies_for[0].monthly_value_usd == 0


def test_insurance_check_endpoint_maps_errors_to_502():
    res = post_insurance_check(InsuranceAgent(client=fake_client(status=500), model="test-model"))
    assert res.status_code == 502
