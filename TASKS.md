# Tasks

Claim a task by putting your name next to it in a PR (or tell the team), then
check it off when the PR merges. See `docs/BUILD_PLAN.md` §8 for details.

## Week 1–2: Foundation
- [x] Set up project structure and repo (skeleton, CLAUDE.md, contracts)
- [ ] Scrape and parse all program data — **Person 2**
- [ ] Build ChromaDB index — **Person 2**
- [ ] FastAPI skeleton with `/api/match` stub — **Person 1** (stub returns fixture; replace with real matcher)
- [ ] React quiz wizard UI — **Person 3**

## Week 3–4: Core Logic
- [ ] Hard-rule eligibility matcher — **Person 1**
- [ ] RAG retrieval engine — **Person 2**
- [ ] Wire quiz frontend to backend API — **Person 3**
- [x] Insurance agent — **Person 4** (endpoint live; pass RAG context once BenefitsRAG lands)

## Week 5–6: Polish
- [ ] Results dashboard with program cards — **Person 3**
- [ ] Action plan modal — **Person 4**
- [ ] Warning banners for threshold cases — **Person 1**
- [ ] End-to-end testing with 10+ realistic profiles — **all**

## Week 7: Demo Prep
- [ ] Deploy to Vercel (frontend) + Railway (backend)
- [ ] Film demo video — 3 minutes max
- [ ] Prepare 5 demo profiles covering different scenarios
- [ ] Write submission narrative (personal story + impact)
