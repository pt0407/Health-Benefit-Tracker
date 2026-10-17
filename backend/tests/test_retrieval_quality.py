"""Retrieval gate: named expectations on the real committed program records."""

import re

import pytest

from config import PROGRAMS_DIR
from rag.eval_profiles import EVAL_PROFILES, evaluate
from rag.rag_engine import BenefitsRAG, build_facet_queries
from rag.store import load_programs
from tests.rag_fixtures import default_embedding_or_skip

PROGRAMS = load_programs(PROGRAMS_DIR)


@pytest.fixture(scope="session")
def real_rag(tmp_path_factory):
    ef = default_embedding_or_skip()
    engine = BenefitsRAG(tmp_path_factory.mktemp("real_chroma") / "chroma", ef)
    engine.index_programs(PROGRAMS)
    return engine


@pytest.mark.parametrize("ev", EVAL_PROFILES, ids=[e.name for e in EVAL_PROFILES])
def test_named_expectation(real_rag, ev):
    ok, missing, unexpected, ids = evaluate(real_rag, ev)
    assert ok, f"{ev.name}: missing={missing} unexpected={unexpected} got={ids}"


def _by_name(name):
    return next(e for e in EVAL_PROFILES if e.name == name)


def test_relevant_programs_shape(real_rag):
    out = real_rag.retrieve_relevant_programs(_by_name("tx_family_of_4_uninsured").profile, k=10)
    assert isinstance(out, list) and 0 < len(out) <= 10
    assert all(isinstance(s, str) and s.strip() for s in out)
    assert len(set(out)) == len(out)


def test_insurance_context_is_health_only(real_rag):
    profile = _by_name("tx_family_of_4_uninsured").profile
    ctx = real_rag.retrieve_insurance_context(profile)
    assert isinstance(ctx, str) and ctx.strip()
    health_ids = {p.program_id for p in PROGRAMS if p.category == "health"}
    chunk_ids = set(re.findall(r"^Program: .*\[([a-z0-9_]+)\]$", ctx, flags=re.M))
    assert chunk_ids and chunk_ids <= health_ids
    assert {"chip_tx", "childrens_medicaid_tx"} <= chunk_ids
    cats = set(re.findall(r"Category: (\w+)", ctx))
    assert cats == {"health"}


def test_non_tx_profile_gets_no_tx_programs(real_rag):
    profile = {**_by_name("tx_family_of_4_uninsured").profile, "state": "CA"}
    ids = {c.program_id for c in real_rag.retrieve(profile, k=10)}
    assert ids
    assert not [i for i in ids if i.endswith("_tx")]


def test_facet_queries_contain_no_program_names():
    names = {p.name.lower() for p in PROGRAMS}
    for ev in EVAL_PROFILES:
        for q in build_facet_queries(ev.profile):
            for n in names:
                assert n not in q.lower(), f"{ev.name}: query contains {n!r}"
