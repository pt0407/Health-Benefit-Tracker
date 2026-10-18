"""Tests for Ask Civis: retrieval, citation checking, history and the endpoint."""

import json

from fastapi.testclient import TestClient

from agents.ask_agent import AskAgent, alternating_history, source_urls
from agents.rate_limit import RateLimiter, client_ip
from main import app
from models.ask import AskRequest
from routers.benefits import ask_limiter, get_ask_agent
from tests.test_api import SAMPLE_PROFILE
from tests.test_insurance_agent import fake_client


class FakeStore:
    """Returns WIC and SNAP chunks for any query, WIC first."""

    def __init__(self, empty=False):
        self.empty, self.queries, self.where = empty, [], None

    def count(self):
        return 0 if self.empty else 2

    def query(self, texts, n_results, where=None):
        self.queries.append(list(texts))
        self.where = where
        hits = [
            {"id": "wic-1", "text": "WIC serves pregnant women and children under 5.",
             "metadata": {"program_id": "wic_federal"}, "distance": 0.1},
            {"id": "snap-1", "text": "SNAP helps buy food.",
             "metadata": {"program_id": "snap_federal"}, "distance": 0.3},
        ]
        return [hits for _ in texts]


def answer(text="WIC serves children under 5.", cited=("wic_federal",), from_records=True):
    return json.dumps({"answer": text, "cited_program_ids": list(cited), "answered_from_records": from_records})


def agent_with(text=None, captured=None, store=None, **kw):
    return AskAgent(client=fake_client(text=text or answer(**kw), captured=captured),
                    store=store or FakeStore(), model="test-model")


def test_answer_cites_only_retrieved_programs_with_record_urls():
    agent = agent_with(cited=("wic_federal", "made_up_program", "chip_tx"))
    result = agent.run(AskRequest(question="Can my toddler get WIC?"))
    assert [s.program_id for s in result.sources] == ["wic_federal"]
    assert result.sources[0].url == source_urls().get("wic_federal", agent.programs["wic_federal"].application_url)
    assert result.answered_from_records


def test_prompt_contains_records_question_and_household():
    captured = []
    agent = agent_with(captured=captured)
    agent.run(AskRequest(question="Do I qualify for WIC?", profile=SAMPLE_PROFILE))
    content = captured[0]["messages"][-1]["content"]
    assert "[wic_federal]" in content and "<question>\nDo I qualify for WIC?" in content
    assert "<household>" in content
    assert "only from the program records" in captured[0]["system"].lower()


def test_search_is_limited_to_federal_and_the_users_state():
    store = FakeStore()
    agent_with(store=store).run(AskRequest(question="food help?"))
    assert store.where == {"state": {"$in": ["TX", "US"]}}


def test_follow_up_also_searches_with_the_previous_question():
    store = FakeStore()
    agent_with(store=store).run(AskRequest(question="What documents do I need?", history=[
        {"role": "user", "content": "Can I get SNAP?"}, {"role": "assistant", "content": "Maybe."}]))
    assert store.queries[0] == ["What documents do I need?", "Can I get SNAP? What documents do I need?"]


def test_history_is_made_alternating_and_ends_with_the_assistant():
    req = AskRequest(question="ok?", history=[
        {"role": "assistant", "content": "hello"}, {"role": "user", "content": "a"},
        {"role": "user", "content": "b"}, {"role": "assistant", "content": "c"}, {"role": "user", "content": "d"}])
    assert alternating_history(req) == [{"role": "user", "content": "a"}, {"role": "assistant", "content": "c"}]


def test_unanswerable_questions_are_flagged_and_em_dashes_removed():
    agent = agent_with(text=answer("The records don’t say — call 2-1-1.", cited=(), from_records=False))
    result = agent.run(AskRequest(question="What is the capital of France?"))
    assert not result.answered_from_records and result.sources == []
    assert "—" not in result.answer


def post_ask(agent, body=None, headers=None):
    app.dependency_overrides[get_ask_agent] = lambda: agent
    try:
        return TestClient(app).post("/api/ask", json=body or {"question": "Can I get WIC?"}, headers=headers or {})
    finally:
        app.dependency_overrides.clear()


def test_endpoint_returns_answer():
    ask_limiter._clients.clear(); ask_limiter._all.clear()
    res = post_ask(agent_with())
    assert res.status_code == 200 and res.json()["sources"][0]["program_id"] == "wic_federal"


def test_endpoint_maps_missing_index_to_503_and_api_errors_to_502():
    ask_limiter._clients.clear(); ask_limiter._all.clear()
    assert post_ask(agent_with(store=FakeStore(empty=True))).status_code == 503
    broken = AskAgent(client=fake_client(status=500), store=FakeStore(), model="test-model")
    assert post_ask(broken).status_code == 502


def test_endpoint_rejects_long_questions():
    assert post_ask(agent_with(), {"question": "x" * 501}).status_code == 422


def test_endpoint_rate_limits_each_client():
    ask_limiter._clients.clear(); ask_limiter._all.clear()
    agent = agent_with()
    codes = [post_ask(agent, headers={"X-Forwarded-For": "1.2.3.4"}).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429
    assert post_ask(agent, headers={"X-Forwarded-For": "5.6.7.8"}).status_code == 200
    ask_limiter._clients.clear(); ask_limiter._all.clear()


def test_rate_limiter_window_and_total_cap():
    now = [0.0]
    limiter = RateLimiter(per_client=2, client_window_s=10, total=3, total_window_s=100, clock=lambda: now[0])
    assert limiter.allow("a") and limiter.allow("a") and not limiter.allow("a")
    now[0] = 11
    assert limiter.allow("a")          # client window passed
    assert not limiter.allow("b")      # total cap of 3 per 100s reached


def test_client_ip_uses_the_proxy_appended_address():
    assert client_ip({"x-forwarded-for": "6.6.6.6, 1.2.3.4"}, "fallback") == "1.2.3.4"
    assert client_ip({}, "fallback") == "fallback"
