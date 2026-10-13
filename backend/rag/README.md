# backend/rag: benefit program retrieval

This package turns the program records in `data/programs/*.json` into a ChromaDB index and
retrieves the programs that fit a household. It uses Chroma's built-in local embedding model,
needs no API key, and puts no model name in code.

| File | Role |
|---|---|
| `chunker.py` | Turns each `Program` into self-describing text chunks with metadata |
| `store.py` | Loads and validates records, wraps the Chroma collection |
| `rag_engine.py` | `BenefitsRAG`: facet queries, rank fusion, filters, public API |

## Build and check the index

The index (`data/chroma_db/`) is gitignored and is NOT committed. Build it before any use.
Run from the repo root with the backend venv active. The first run downloads Chroma's default
embedding model (about 80 MB, cached under `~/.cache/chroma`).

```
python data/scripts/index_to_chromadb.py          # rebuild data/chroma_db/ from data/programs/*.json
python data/scripts/index_to_chromadb.py --check  # INDEX OK or INDEX STALE (exit 1)
python data/scripts/check_retrieval.py            # named retrieval expectations
cd backend && pytest
```

Rebuild whenever anything in `data/programs/` changes.

## API

```python
from rag.rag_engine import BenefitsRAG, IndexNotBuiltError

rag = BenefitsRAG()                         # default dir: config.CHROMA_DIR
ids = rag.retrieve(profile, k=10)           # list[RetrievedChunk]
texts = rag.retrieve_relevant_programs(profile)   # list[str], unique chunk texts, best first
context = rag.retrieve_insurance_context(profile) # one string, category "health" only
```

`profile` is a `UserProfile` or a dict. Methods:

- `retrieve(profile, k=10, categories=None)`: `RetrievedChunk` objects (`text`, `program_id`, `program_name`, `category`, `source`, `score`, plus `chunk_id`, `section`).
- `retrieve_relevant_programs(profile, k=10)`: `list[str]`, at most `k` non-empty, unique chunk texts.
- `retrieve_context(profile, k=10, categories=None)`: chunks joined by a blank line.
- `retrieve_insurance_context(profile, k=8)`: health programs only, one string.
- `index_programs(programs)`: full rebuild, idempotent.
- `facet_queries(profile)`: the exact query texts sent to the index.

A missing or empty index raises `IndexNotBuiltError`; its message names
`python data/scripts/index_to_chromadb.py`. A web route should turn it into HTTP 503.

Retrieval is deterministic: several short facet queries are built from the household description
(never from program names or IDs), run with a state filter (`US` plus the profile's state), fused
by rank, and capped at 2 chunks per program. Programs whose `requires_pregnancy`,
`requires_children` or `requires_disability` flag is true are dropped when the profile clearly
lacks that condition.

## Chunk format

Each chunk is self-describing so it can be pasted into a prompt alone:

```
Program: <name> [<program_id>]
Type: <type> | Category: <category> | Source: <source> | Last updated: <last_updated>
<body>
Apply: <application_url>
```

Sections per program: `overview` (the description), `eligibility` (sentences rendered from the
structured fields; a null income limit reads "No single percent-of-poverty income limit is
recorded"), and `apply` (documents, processing time, estimated monthly value, "not recorded"
when null). Bodies are at most 300 words; longer ones split on sentence boundaries with up to 50
words of overlap. Chunk ID: `<program_id>:<section>:<n>`. Metadata: `program_id`, `program_name`,
`type`, `category`, `state` (`TX` when the ID ends in `_tx`, else `US`), `source`, `section`,
`chunk_index`, `requires_children`, `requires_disability`, `requires_pregnancy`.

## What the engine does not do

- It makes no eligibility decisions. Eligibility belongs to the matcher.
- It does no income math and applies no income or age rules.
- It does not call any LLM.

## Traps when reading the records

Short form; the full list is in [../../data/README.md](../../data/README.md).

- `income_limit_pct_fpl` is the highest band for banded programs, not a simple cutoff. The bands are in `description`.
- SNAP is recorded at the Texas gross limit of 165 percent, not the federal 130.
- `processing_time_days` is in calendar days (business days are converted).
- `null` means not applicable or no official basis, never zero. A null income limit means do not apply an income test.
- Some values are estimates. Detect them in the sidecar: `sidecar[program_id]["fields"][field].get("estimated") is True`, where the sidecar is `data/sources/<federal|texas>_sources.json`. Health coverage values are government spending per enrollee, not cash the household receives.
