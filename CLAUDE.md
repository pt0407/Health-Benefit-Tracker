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
