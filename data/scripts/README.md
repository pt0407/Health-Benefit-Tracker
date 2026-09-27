# Data scripts (Owner: Person 2)

Run in order from the repo root:

1. `scrape_benefits_data.py` — download source data into `data/raw/` (gitignored)
2. `parse_programs.py` — write structured programs to `data/programs/*.json`
3. `index_to_chromadb.py` — embed and store in `data/chroma_db/` (gitignored)

Every entry in `data/programs/*.json` must validate against
`backend/models/program.py`; `cd backend && pytest` checks this.
