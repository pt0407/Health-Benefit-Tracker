# BenefitsFinder

*Find the benefits you're owed. In minutes.*

A web app that asks 10 simple questions and surfaces every federal and Texas
benefit program you likely qualify for, with exact next steps to apply.
Built for the Congressional App Challenge 2026.

- Product plan: [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md)
- Team rules & ownership: [`CLAUDE.md`](CLAUDE.md)
- Task board: [`TASKS.md`](TASKS.md)

## Running locally

**Backend** (Python 3.11):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

**Frontend** (Node 22+):

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (calls to `/api` are proxied to the backend).

## Tests

```bash
cd backend && pytest
cd frontend && npm run build
```
