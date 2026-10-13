# BenefitsFinder — Rules for every Claude Code agent

This repo is worked on by **4 people, each running their own Claude Code agent**.
Read this whole file before making changes. The full product plan is in
[`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md); open tasks and who owns them are in
[`TASKS.md`](TASKS.md).

## Git workflow (non-negotiable)

1. **Never push to `main`.** All changes go through a pull request.
2. **One branch per task.** Name it `<owner>/<short-task>` (e.g. `p3/quiz-wizard`).
   If your harness assigns a branch name, use that.
3. **Start from fresh `main`:** `git fetch origin main && git checkout -b <branch> origin/main`.
4. **Before opening a PR**, merge the latest `main` into your branch and make sure
   the checks below pass.
5. **Never rewrite history** on a branch someone else pushed to (no rebase,
   amend or force-push on shared branches).
6. **Keep PRs small** — one feature or fix each, ideally < 400 changed lines.
7. **Stay in your lane.** Only edit files your owner owns (table below). If you
   need a change in someone else's file, keep it minimal and call it out in the PR
   description, or open an issue instead.

## Ownership

| Owner | Area | Files |
|---|---|---|
| Person 1 | Backend API + Eligibility Matcher | `backend/main.py`, `backend/routers/`, `backend/matching/` |
| Person 2 | RAG Engine + Knowledge Base | `backend/rag/`, `data/` |
| Person 3 | Frontend Quiz + Results Dashboard | `frontend/` (except `ActionPlan.jsx`) |
| Person 4 | Insurance Agent + Action Plan | `backend/agents/`, `frontend/src/components/Results/ActionPlan.jsx` |

**Shared contracts** — `backend/models/`, `backend/fixtures/`, and this file —
affect everyone. Change them only in a PR dedicated to that change, and say so
in the title (`[contract] ...`). Keep changes backward compatible where possible.

## Shared contracts

- **Request/response shapes** for every endpoint live in `backend/models/`
  (Pydantic). The frontend must match these field names exactly.
- **`backend/fixtures/sample_match_response.json`** is a realistic example
  response for `POST /api/match`. Until the real matcher lands, the endpoint
  returns this fixture so the frontend can be built in parallel.
- **Program data schema** is `backend/models/program.py`; every entry in
  `data/programs/*.json` must validate against it (a test enforces this).

## Tech stack

- **Backend:** Python 3.11, FastAPI, Pydantic v2, Anthropic Python SDK,
  LangChain + ChromaDB, pytest. Run from `backend/`.
- **Frontend:** React 18 + Vite, React Router, TailwindCSS v4, Recharts, Axios.
  Run from `frontend/`. The Vite dev server proxies `/api` to `localhost:8000`.

## Corrections to the build plan

The plan in `docs/BUILD_PLAN.md` has a couple of things that won't work as written:

- **No `AnthropicEmbeddings`.** Anthropic does not offer an embeddings API. Use
  ChromaDB's built-in default embedding function (local, free, no key), or
  Voyage AI if we need better quality later.
- **Don't `json.loads(response.content[0].text)`.** Use the SDK's structured
  outputs: `client.messages.parse(..., output_format=SomePydanticModel)` and
  read `response.parsed_output`. It guarantees valid JSON matching the schema.
- **Model ID** is configured once in `backend/config.py` (`CLAUDE_MODEL`,
  overridable by env var). Don't hard-code model IDs elsewhere.
- **`chroma_db/` is generated, not committed.** It's in `.gitignore`. Anyone
  can rebuild it with the scripts in `data/scripts/`. Binary DB files in git
  cause unresolvable merge conflicts.

## Checks to run before every PR

```bash
# backend
cd backend && pytest

# frontend
cd frontend && npm run build
```

## Secrets

Never commit API keys. The backend reads `ANTHROPIC_API_KEY` from the
environment (or `backend/.env`, which is gitignored). See `backend/.env.example`.

<!-- BEGIN: Person 2 data and RAG guidance -->
## Consuming Person 2's data and RAG engine (all agents)

### For every agent

- Program records: `data/programs/federal_programs.json` and `data/programs/texas_programs.json` (schema: `backend/models/program.py`). Per-field sources and estimate markers: `data/sources/federal_sources.json` and `data/sources/texas_sources.json` (keyed by `program_id`, then `fields`). Docs: `data/README.md`, `data/scripts/README.md`, `backend/rag/README.md`. Read them before using a field.
- Build the index before using `BenefitsRAG` (it is not committed): `python data/scripts/index_to_chromadb.py`. Rebuild after any change in `data/programs/`.
- Do NOT edit `data/` or `backend/rag/` unless you are Person 2. Open an issue instead.
- `null` means not applicable, no income test, or no official basis. It never means zero. Never treat null as 0.
- `income_limit_pct_fpl` for banded programs stores the HIGHEST band. It is not a simple cutoff. Every band is listed in the record's `description`. Example: a child's program can store the infant band while older children have a lower limit.
- SNAP (`snap_federal`) stores the Texas gross limit of 165 percent, not the federal 130.
- `processing_time_days` is in CALENDAR days. Business-day standards were converted.
- Some dollar values and percents are estimates, not figures an agency states verbatim. Detect them with `sidecar[program_id]["fields"][field].get("estimated") is True`, where `sidecar` is the parsed `data/sources/*_sources.json`. The estimate's method, meaning and inputs are in that entry's `estimate` object. Health coverage values (Medicaid, CHIP) are government spending per enrollee, NOT cash the household receives. A null in these fields has a `null_reason` in the sidecar.
- Never print an estimated value as if an agency stated it. Never present spending per enrollee as money a household gets.

### Person 1 (matcher and API)

- `backend/matching/eligibility_matcher.py` hard-codes 130 for SNAP. The records use 165 for a Texas applicant. Update the matcher or the two will disagree.
- The matcher uses the 2025 HHS poverty table. The 2026 guidelines are in effect: read the values from https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines and update the table. Percent fields in the records are not affected, dollar conversions in the matcher are.
- Do not treat `income_limit_pct_fpl` as a simple cutoff for banded programs (see above). A null limit means skip the income test for that program.
- Totals you compute from `estimated_monthly_value_usd` now include estimated values. Tell Person 3 so the UI can label them.
- Construct the engine once at startup and pass it to the matcher:

```python
from rag.rag_engine import BenefitsRAG, IndexNotBuiltError

rag = BenefitsRAG()                                # uses config.CHROMA_DIR, no API key
chunks = rag.retrieve_relevant_programs(profile)   # list[str], best matches first
hits = rag.retrieve(profile, k=10)                 # RetrievedChunk: program_id, program_name, category, source, score, text
```

- Insurance route (`backend/routers/benefits.py`): keep the path and decorator, change the parameters and body. `IndexNotBuiltError` must become HTTP 503:

```python
def get_rag() -> BenefitsRAG:
    return BenefitsRAG()

def insurance_check(profile: UserProfile, agent: InsuranceAgent = Depends(get_insurance_agent),
                    rag: BenefitsRAG = Depends(get_rag)) -> InsuranceResult:
    try:
        rag_context = rag.retrieve_insurance_context(profile)   # one string, health programs only
        return agent.run(profile, rag_context)
    except IndexNotBuiltError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except InsuranceAgentError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
```

- The engine only retrieves text. It makes no eligibility decisions and does no income math.

### Person 3 (frontend)

- The results dashboard currently shows estimated values and totals as plain numbers.
- Before changing or shipping the results UI, the Person 3 agent MUST ask Person 3 how estimates should be labeled. It MUST NOT decide that on its own.
- `MatchResponse` exposes no estimate flag today. Any such field is a separate `[contract]` change made by its owner.

### Person 4 (insurance agent)

`retrieve_insurance_context(profile)` returns ONE string, which is what `rag_context` expects. The records differ from `backend/agents/insurance_rules.py` in these ways; reconcile the rules text or confirm the records are right:

1. CHIP Perinatal: the rules say it covers prenatal care and delivery. Officially, for women at or below 198 percent of the poverty level, hospital delivery charges are paid through Emergency Medicaid and CHIP Perinatal covers two postpartum visits.
2. MEPD (Medicaid for the Elderly and People with Disabilities): the rules say "SSI-level income". Officially, community programs use the SSI-based limit, but nursing facility, waiver and attendant care programs use a higher special income limit.
3. Parent and caretaker Medicaid ("well under 20% FPL"): not among the Person 2 records and not verified. The handbook publishes it only in dollars.
4. Emergency Medicaid: the record stores a percent that applies to pregnant women and young children only. The rules give no percent.
5. SNAP is not in the rules text. The record uses the Texas gross limit of 165 percent, not 130.
6. Medicaid (overview) and SSDI records require citizenship or a qualifying status. The rules do not say how Medicaid treats immigration status beyond Emergency Medicaid and CHIP Perinatal.
7. Medicare Extra Help: the record stores 150 percent FPL; Medicare.gov states the limits in dollars plus resource limits.
8. Processing time for Medicaid for Pregnant Women and CHIP Perinatal was 15 business days at the source and is stored in calendar days. Do not print the stored number as "15 days".

The source link for each item is in the matching record's sidecar entry; ask Person 2 for the full comparison notes.
<!-- END: Person 2 data and RAG guidance -->
