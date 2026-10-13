"""Synthetic programs and helpers for the RAG tests. Nothing here is real program data."""

import hashlib
import json
from pathlib import Path

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from models.program import Eligibility, Program

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_SCRIPT = REPO_ROOT / "data" / "scripts" / "index_to_chromadb.py"


def _program(program_id, name, type_, category, description, url_slug, pct=None, docs=(),
             days=None, value=None, **eligibility):
    return Program(
        program_id=program_id, name=name, type=type_, category=category,
        description=description, eligibility=Eligibility(income_limit_pct_fpl=pct, **eligibility),
        estimated_monthly_value_usd=value, application_url=f"https://example.org/apply/{url_slug}",
        documents_needed=list(docs), processing_time_days=days, source="Example Agency",
        last_updated="2026-01-01",
    )


FIXTURE_PROGRAMS = [
    _program("example_food_help_federal", "Example Food Help", "federal", "nutrition",
             "Monthly grocery money on a card for low-income households who need help buying food.",
             "food", pct=130, docs=["ID", "Proof of income"], days=30, value=250.5),
    _program("example_kids_health_plan_tx", "Example Kids Health Plan (TX)", "federal_state", "health",
             "Low-cost health insurance for children in families that earn too much for free "
             "children's coverage. Covers doctor visits, vaccines and dental care.",
             "kids", pct=201, docs=["Proof of income", "Child's birth certificate"], days=45,
             requires_children=True),
    _program("example_senior_drug_help_federal", "Example Senior Prescription Help", "federal", "health",
             "Help paying prescription drug premiums and copays for older adults who are on "
             "limited incomes. Reduces the cost of medicine for people age 65 or older.",
             "senior", pct=150, days=21, value=80, age_min=65, citizenship_required=True),
    _program("example_pregnancy_care_tx", "Example Pregnancy Care (TX)", "state", "health",
             "Prenatal visits, labor and delivery, and care after the birth for pregnant women "
             "who have no health insurance.",
             "pregnancy", pct=202, docs=["Proof of pregnancy"], days=15, requires_pregnancy=True),
    _program("example_utility_help_federal", "Example Utility Bill Help", "federal", "utilities",
             "Helps low-income households pay electricity, heating and cooling bills, and "
             "avoid shutoffs when the bill cannot be paid.",
             "utility", pct=150, docs=["Latest utility bill"], days=14, value=300),
    _program("example_disability_income_federal", "Example Disability Income", "federal", "cash",
             "Monthly cash payments for adults whose disability keeps them from working. "
             "Based on past work history rather than a single income limit.",
             "disability", days=120, requires_disability=True, citizenship_required=True),
]


class HashEmbedding(EmbeddingFunction[Documents]):
    """Deterministic bag-of-words hashing embedding for plumbing tests (no model download)."""

    def __init__(self, dims: int = 64) -> None:
        self.dims = dims

    def __call__(self, input: Documents):
        vectors = []
        for text in input:
            v = np.full(self.dims, 1e-3, dtype=np.float32)
            for word in text.lower().split():
                v[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dims] += 1.0
            vectors.append(v)
        return vectors

    @staticmethod
    def name() -> str:
        return "test_hash_embedding"

    def get_config(self) -> dict:
        return {"dims": self.dims}

    @staticmethod
    def build_from_config(config: dict) -> "HashEmbedding":
        return HashEmbedding(config.get("dims", 64))


def write_programs_dir(directory: Path, programs=FIXTURE_PROGRAMS) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fixture_programs.json").write_text(
        json.dumps([p.model_dump() for p in programs], indent=2), encoding="utf-8")
    return directory


def default_embedding_or_skip():
    """Chroma's real default embedding function; skip only if its model cannot be loaded."""
    import pytest

    ef = DefaultEmbeddingFunction()
    try:
        ef(["probe"])
    except Exception as exc:  # model missing and no network
        pytest.skip(f"default embedding model unavailable: {exc}")
    return ef
