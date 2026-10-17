"""Component 4: RAG engine. Owner: Person 2.

See docs/BUILD_PLAN.md section 3 (Component 4) and AUTON/PLAN.md Appendix C.
Embeddings come from ChromaDB's built-in default embedding function (local, no
API key). The vector DB persists to config.CHROMA_DIR (gitignored) and is built
by data/scripts/index_to_chromadb.py.

The engine only retrieves program text. It does not decide eligibility and it
does not compute poverty-level percentages; that belongs to the matcher.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from models.program import Program
from models.user_profile import UserProfile
from rag.store import COLLECTION_NAME, ChunkStore

REBUILD_COMMAND = "python data/scripts/index_to_chromadb.py"
MAX_CHUNKS_PER_PROGRAM = 2
HUB_PENALTY = 0.5
SEED_BONUS = 1.0  # large enough that seeded chunks sort ahead of every unseeded chunk
FACET_DEPTH = 8  # a facet only credits chunks ranked within its top few: deeper matches are loose and noisy
RRF_K = 10  # reciprocal rank fusion constant; small so rank position matters on a small corpus

# Facet weights. Conditions the household actually has outrank generic needs.
SITUATION, BASIC_NEED, BACKGROUND = 1.5, 0.5, 0.25
CORE_NEED = 0.7  # food and utility bills: needs of every low-income household


class IndexNotBuiltError(RuntimeError):
    """The vector index is missing or empty."""


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    program_id: str
    program_name: str
    category: str
    source: str
    score: float  # fused reciprocal-rank score, higher is better
    chunk_id: str = ""
    section: str = ""


def _as_profile(profile) -> UserProfile:
    return profile if isinstance(profile, UserProfile) else UserProfile.model_validate(profile)


def _children_phrase(ages: list[int]) -> str:
    if not ages:
        return "children in the household"
    shown = [str(a) for a in sorted(ages)]
    if len(shown) == 1:
        return f"a child aged {shown[0]}"
    return f"children aged {', '.join(shown[:-1])} and {shown[-1]}"


_HEALTH_BY_INSURANCE = {
    "uninsured": ("person with no health insurance who needs free or low-cost health coverage", SITUATION),
    "employer": ("person with health insurance through an employer who needs help with medical costs", BASIC_NEED),
    "marketplace": ("person who buys health insurance on the marketplace and needs lower monthly premiums", BASIC_NEED),
    "medicaid_medicare": ("person who already has government health coverage for low-income or older people "
                          "and needs help with remaining costs", BASIC_NEED),
    "other": ("person with other health insurance who needs help with medical costs", BASIC_NEED),
}


def _facets(profile: UserProfile) -> list[tuple[str, float]]:
    """Short plain-language descriptions of the household, each with a fusion weight.

    They never contain program names or program IDs.
    """
    people = "1 person" if profile.household_size == 1 else f"{profile.household_size} people"
    income = "no income" if profile.annual_income == 0 else f"an annual income of ${profile.annual_income:,}"
    facets = [
        (f"household of {people} with {income} that needs financial help", BACKGROUND),
        ("low-income household that needs help paying for groceries and food", CORE_NEED),
        ("low-income household that needs help paying electricity, heating, cooling and other utility bills",
         CORE_NEED),
        _HEALTH_BY_INSURANCE[profile.insurance_status],
    ]
    if profile.has_children or profile.children_ages or profile.is_pregnant:
        # The child and pregnancy facets below are sharper than the general coverage need.
        facets[-1] = (facets[-1][0], BACKGROUND)
    ages = list(profile.children_ages)
    if profile.has_children or ages:
        kids = _children_phrase(ages)
        facets.append((f"family with {kids} who needs free or low-cost health coverage for the children", SITUATION))
        facets.append((f"family with {kids} who needs monthly cash help to pay for basic expenses", SITUATION))
        if any(a < 5 for a in ages):
            facets.append(("baby or young child under age 5 who needs healthy food, formula and nutrition support",
                           SITUATION))
    if profile.is_pregnant:
        facets.append(("pregnant woman who needs prenatal care, delivery costs and health coverage during pregnancy",
                       SITUATION))
        facets.append(("pregnant woman who needs healthy food and nutrition support for herself and her baby",
                       SITUATION))
    if profile.age >= 65:
        facets.append((f"older adult aged {profile.age}, age 65 or older, on a limited income who needs help "
                       "paying for health care and prescription drugs", SITUATION))
    if profile.has_disability or profile.receiving_disability_benefits:
        facets.append(("adult with a disability who cannot work and needs monthly income and health coverage",
                       SITUATION))
    if profile.employment_status == "recently_unemployed":
        facets.append(("worker who recently lost a job through no fault of their own and needs weekly income replacement while "
                       "looking for new work",
                       SITUATION))
    elif profile.employment_status == "unemployed":
        facets.append(("unemployed adult without a job who needs income while looking for work", SITUATION))
    if profile.citizenship == "not_citizen":
        facets.append(("immigrant who is not a U.S. citizen or lawful permanent resident and needs emergency "
                       "medical care", SITUATION))
    elif profile.citizenship == "citizen":
        facets.append(("U.S. citizen or lawful permanent resident with a low income", BACKGROUND))
    return facets


def build_facet_queries(profile) -> list[str]:
    """The query texts retrieve() sends to the index for this profile."""
    return [text for text, _ in _facets(_as_profile(profile))]


def _where(profile: UserProfile, categories: Optional[set[str]]) -> dict:
    clauses: list[dict] = [{"state": {"$in": list(dict.fromkeys(["US", profile.state.upper()]))}}]
    # Drop programs that require a condition the profile clearly lacks.
    if not profile.is_pregnant:
        clauses.append({"requires_pregnancy": False})
    if not (profile.has_children or profile.children_ages):
        clauses.append({"requires_children": False})
    if not (profile.has_disability or profile.receiving_disability_benefits):
        clauses.append({"requires_disability": False})
    if categories:
        clauses.append({"category": {"$in": sorted(categories)}})
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


class BenefitsRAG:
    def __init__(self, persist_dir: Optional[Path] = None, embedding_function=None,
                 collection_name: str = COLLECTION_NAME) -> None:
        self._store = ChunkStore(persist_dir, embedding_function, collection_name)

    def index_programs(self, programs: list[Program]) -> None:
        """Full rebuild of the index from programs. Safe to call repeatedly."""
        self._store.rebuild(programs)

    def facet_queries(self, profile) -> list[str]:
        return build_facet_queries(profile)

    def retrieve(self, profile, k: int = 10, categories: Optional[set[str]] = None) -> list[RetrievedChunk]:
        profile = _as_profile(profile)
        if self._store.count() == 0:
            raise IndexNotBuiltError(
                f"The benefits index at {self._store.persist_dir} is missing or empty. "
                f"Build it with: {REBUILD_COMMAND}")
        if k < 1 or (categories is not None and not categories):
            return []
        facets = _facets(profile)
        results = self._store.query([text for text, _ in facets], max(2 * k, 16), _where(profile, categories))
        scores: dict[str, float] = {}
        generic: dict[str, float] = {}
        seeds: set[str] = set()
        hits: dict[str, dict] = {}
        for (_, weight), ranked in zip(facets, results):
            if ranked and weight >= CORE_NEED:
                # Round-robin seat: the best match for each household need or situation is always in play.
                seeds.add(ranked[0]["id"])
            for rank, hit in enumerate(ranked[:FACET_DEPTH], start=1):
                scores[hit["id"]] = scores.get(hit["id"], 0.0) + weight / (RRF_K + rank)
                if weight != CORE_NEED:  # food and utility matches are what those programs are for
                    generic[hit["id"]] = generic.get(hit["id"], 0.0) + 1.0 / (RRF_K + rank)
                hits[hit["id"]] = hit
        # Hub damping: a chunk that is a loose match for every facet is less specific than one that is
        # a tight match for a few, so subtract part of its unweighted overall similarity.
        for cid in scores:
            scores[cid] -= HUB_PENALTY * generic.get(cid, 0.0)
            if cid in seeds:
                scores[cid] += SEED_BONUS
        chunks = []
        per_program: Counter = Counter()
        for cid in sorted(scores, key=lambda cid: (-scores[cid], cid)):
            meta = hits[cid]["metadata"]
            if len(chunks) == k:
                break
            if per_program[meta["program_id"]] == MAX_CHUNKS_PER_PROGRAM:
                continue
            per_program[meta["program_id"]] += 1
            chunks.append(RetrievedChunk(
                text=hits[cid]["text"], program_id=meta["program_id"], program_name=meta["program_name"],
                category=meta["category"], source=meta["source"], score=scores[cid],
                chunk_id=cid, section=meta["section"]))
        return chunks

    def retrieve_relevant_programs(self, profile, k: int = 10) -> list[str]:
        """Chunk texts (self-describing, unique) for the best-matching programs."""
        return list(dict.fromkeys(chunk.text for chunk in self.retrieve(profile, k)))

    def retrieve_context(self, profile, k: int = 10, categories: Optional[set[str]] = None) -> str:
        return "\n\n".join(chunk.text for chunk in self.retrieve(profile, k, categories))

    def retrieve_insurance_context(self, profile, k: int = 8) -> str:
        """Retrieved text for the insurance agent: health-category programs only."""
        return self.retrieve_context(profile, k, categories={"health"})
