# Tasks

Claim a task by putting your name next to it in a PR (or tell the team), then
check it off when the PR merges. See `docs/BUILD_PLAN.md` §8 for details.

## Week 1–2: Foundation
- [x] Set up project structure and repo (skeleton, CLAUDE.md, contracts)
- [x] Scrape and parse all program data — **Person 2**
- [x] Build ChromaDB index — **Person 2**
- [x] FastAPI skeleton with `/api/match` stub — **Person 1**
- [x] React quiz wizard UI — **Person 3** (#16, estimate labels from #18)

## Week 3–4: Core Logic
- [x] Hard-rule eligibility matcher — **Person 1** (#15)
- [x] RAG retrieval engine — **Person 2**
- [x] Wire quiz frontend to backend API — **Person 3** (#16)
- [x] Insurance agent — **Person 4** (#1, uses RAG context)

## Week 5–6: Polish
- [x] Results dashboard with program cards — **Person 3** (#16)
- [x] Action plan modal — **Person 4**
- [x] Warning banners for threshold cases — **Person 1** (#15)
- [ ] End-to-end testing with 10+ realistic profiles — **all**

## Still open
- [ ] Run the insurance agent against the real API with the RAG index (`python -m agents.run_insurance_profiles`) — **Person 4**
- [ ] Verify the ACA Marketplace rules in `backend/agents/insurance_rules.py` against an official source — **Person 4**
- [ ] Decide on open PRs #14 (quiz design doc), #17 (PDF worksheet) and #18 (superseded by #16) — **all**

## Week 7: Demo Prep
- [ ] Deploy to Vercel (frontend) + Railway (backend)
- [ ] Film demo video — 3 minutes max
- [ ] Prepare 5 demo profiles covering different scenarios
- [ ] Write submission narrative (personal story + impact)
