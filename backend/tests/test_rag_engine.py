import re
from collections import Counter

import pytest

from models.user_profile import UserProfile
from rag.rag_engine import BenefitsRAG, IndexNotBuiltError, RetrievedChunk, build_facet_queries
from tests.rag_fixtures import FIXTURE_PROGRAMS, HashEmbedding, default_embedding_or_skip

BASE = dict(state="TX", household_size=3, annual_income=18000, employment_status="employed", age=34,
            has_children=False, children_ages=[], is_pregnant=False, has_disability=False,
            insurance_status="uninsured", citizenship="citizen")
FAMILY = dict(household_size=4, annual_income=32000, has_children=True, children_ages=[6, 8])
SENIOR = dict(household_size=1, annual_income=16000, employment_status="unemployed", age=67,
              insurance_status="medicaid_medicare")
ALL_IDS = {p.program_id for p in FIXTURE_PROGRAMS}


def make_profile(**overrides) -> UserProfile:
    return UserProfile(**{**BASE, **overrides})


def ids_of(chunks) -> set:
    return {c.program_id for c in chunks}


@pytest.fixture
def rag(tmp_path):
    engine = BenefitsRAG(tmp_path / "chroma", HashEmbedding())
    engine.index_programs(FIXTURE_PROGRAMS)
    return engine


@pytest.fixture(scope="module")
def semantic_rag(tmp_path_factory):
    engine = BenefitsRAG(tmp_path_factory.mktemp("semantic") / "chroma", default_embedding_or_skip())
    engine.index_programs(FIXTURE_PROGRAMS)
    return engine


def test_return_types_and_length(rag):
    chunks = rag.retrieve(make_profile(**FAMILY), k=3)
    assert len(chunks) == 3 and all(isinstance(c, RetrievedChunk) for c in chunks)
    assert all(c.text.startswith("Program: ") and c.program_id and c.program_name and c.category and c.source
               for c in chunks)
    texts = rag.retrieve_relevant_programs(make_profile(**FAMILY), k=3)
    assert isinstance(texts, list) and 0 < len(texts) <= 3 and all(isinstance(t, str) and t for t in texts)
    assert rag.retrieve(make_profile(**FAMILY), k=0) == []


def test_no_duplicates_and_per_program_cap(rag):
    chunks = rag.retrieve(make_profile(**FAMILY), k=50)
    assert len({c.chunk_id for c in chunks}) == len(chunks) == len({c.text for c in chunks})
    counts = Counter(c.program_id for c in chunks)
    assert max(counts.values()) == 2
    assert len(chunks) == 8  # four programs apply to this household, two chunks each
    assert len(set(rag.retrieve_relevant_programs(make_profile(**FAMILY), k=50))) == 8


def test_best_chunk_of_each_program_comes_before_second_chunks(rag):
    assert len(ids_of(rag.retrieve(make_profile(**FAMILY), k=4))) == 4


def test_non_texas_profile_gets_no_tx_programs(rag):
    tx_ids = ids_of(rag.retrieve(make_profile(**FAMILY), k=50))
    ca_ids = ids_of(rag.retrieve(make_profile(state="CA", **FAMILY), k=50))
    assert "example_kids_health_plan_tx" in tx_ids
    assert ca_ids and not any(i.endswith("_tx") for i in ca_ids)


def test_category_filter(rag):
    profile = make_profile(**FAMILY)
    assert {c.category for c in rag.retrieve(profile, k=50, categories={"health"})} == {"health"}
    assert {c.category for c in rag.retrieve(profile, k=50, categories={"nutrition", "utilities"})} == {
        "nutrition", "utilities"}
    assert rag.retrieve(profile, k=50, categories=set()) == []


def test_dict_profile_is_accepted(rag):
    profile = make_profile(**FAMILY)
    assert rag.retrieve(profile.model_dump(), k=5) == rag.retrieve(profile, k=5)
    assert rag.retrieve_relevant_programs({**BASE, **FAMILY}, k=5) == rag.retrieve_relevant_programs(profile, k=5)


@pytest.mark.parametrize("overrides, program_id", [
    ({"is_pregnant": True}, "example_pregnancy_care_tx"),
    ({"has_children": True, "children_ages": [3]}, "example_kids_health_plan_tx"),
    ({"has_disability": True}, "example_disability_income_federal"),
    ({"receiving_disability_benefits": True}, "example_disability_income_federal"),
])
def test_programs_requiring_a_missing_condition_are_dropped(rag, overrides, program_id):
    assert program_id not in ids_of(rag.retrieve(make_profile(), k=50))
    assert program_id in ids_of(rag.retrieve(make_profile(**overrides), k=50))


def test_facet_queries_never_name_a_program():
    profiles = [make_profile(), make_profile(**FAMILY), make_profile(**SENIOR),
                make_profile(is_pregnant=True, citizenship="not_citizen"),
                make_profile(has_disability=True, employment_status="recently_unemployed",
                             insurance_status="employer", annual_income=0, household_size=1)]
    real_names = r"\b(medicaid|medicare|chip|snap|wic|tanf|ssi|ssdi|liheap)\b"
    for profile in profiles:
        queries = build_facet_queries(profile)
        assert len(queries) >= 4 and len(set(queries)) == len(queries)
        assert queries == build_facet_queries(profile.model_dump())
        for query in queries:
            lowered = query.lower()
            assert not re.search(real_names, lowered) and "example" not in lowered
            assert not any(p.name.lower() in lowered or p.program_id in lowered for p in FIXTURE_PROGRAMS)


def test_missing_or_empty_index_raises_with_rebuild_command(tmp_path):
    profile = make_profile(**FAMILY)
    missing = BenefitsRAG(tmp_path / "nothing", HashEmbedding())
    for call in (missing.retrieve, missing.retrieve_relevant_programs, missing.retrieve_context,
                 missing.retrieve_insurance_context):
        with pytest.raises(IndexNotBuiltError, match=r"python data/scripts/index_to_chromadb\.py"):
            call(profile)
    assert not (tmp_path / "nothing").exists()
    empty = BenefitsRAG(tmp_path / "empty", HashEmbedding())
    empty.index_programs([])
    with pytest.raises(IndexNotBuiltError):
        empty.retrieve(profile)
    assert issubclass(IndexNotBuiltError, RuntimeError)


def test_retrieve_context_joins_chunks_with_a_blank_line(rag):
    profile = make_profile(**FAMILY)
    context = rag.retrieve_context(profile, k=5)
    assert isinstance(context, str)
    assert context == "\n\n".join(c.text for c in rag.retrieve(profile, k=5))
    assert len(context.split("\n\n")) == 5


def test_insurance_context_is_health_only(rag):
    profile = make_profile(**FAMILY)
    context = rag.retrieve_insurance_context(profile)
    assert context and context == rag.retrieve_context(profile, k=8, categories={"health"})
    blocks = context.split("\n\n")
    assert all("| Category: health |" in b.split("\n")[1] for b in blocks)
    assert "[example_kids_health_plan_tx]" in context


def test_same_input_gives_same_output_and_reindexing_is_idempotent(rag):
    profile = make_profile(**FAMILY)
    first = rag.retrieve(profile, k=8)
    assert rag.retrieve(profile, k=8) == first
    rag.index_programs(FIXTURE_PROGRAMS)
    assert rag.retrieve(profile, k=8) == first


def test_semantic_ranking_with_real_default_embedding(semantic_rag):
    senior = semantic_rag.retrieve(make_profile(**SENIOR), k=10)
    assert senior[0].program_id == "example_senior_drug_help_federal"
    assert senior[0].score > max(c.score for c in senior if c.program_id != senior[0].program_id)
    pregnant = semantic_rag.retrieve(make_profile(household_size=2, annual_income=22000, age=27, is_pregnant=True), k=10)
    assert pregnant[0].program_id == "example_pregnancy_care_tx"
    family = semantic_rag.retrieve(make_profile(**FAMILY), k=10)
    assert "example_senior_drug_help_federal" not in [c.program_id for c in family[:2]]
    assert {"example_kids_health_plan_tx", "example_food_help_federal"} <= ids_of(family)
