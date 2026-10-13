# Data scripts (Owner: Person 2)

## How the data is gathered

The build plan names the Benefits.gov API as the data source. That API was retired
(`benefits.gov` now redirects to USA.gov and `api.benefits.gov` does not respond), so nothing
is scraped from it. The records in `data/programs/*.json` are **hand-curated from official
agency pages** (USDA, HHS, CMS, SSA, Texas HHSC and similar). Every figure is backed by a
per-field entry in `data/sources/<name>_sources.json` that names the official URL and quotes
the supporting text. The scripts here snapshot those pages and check the records against
them; they never generate records.

## Pipeline

Run from the repo root with the backend venv active:

```
python data/scripts/scrape_benefits_data.py            # snapshot cited official pages into data/raw/ (gitignored)
python data/scripts/parse_programs.py --check-evidence # validate records and cross-check figures against snapshots
python data/scripts/index_to_chromadb.py               # rebuild data/chroma_db/ (gitignored) from data/programs/*.json
python data/scripts/check_retrieval.py                 # run the named retrieval expectations
cd backend && pytest
```

- `scrape_benefits_data.py` prints `FETCH <OK|BLOCKED|ERROR> <status or reason> <url>` and a final
  `SUMMARY urls=<n> ok=<n> blocked=<n> error=<n>`. It uses an honest User-Agent, one request per
  second, and never works around 403, 202 or bot checks; blocked pages must be read by hand.
  It writes `data/raw/fetch_log.json`.
- `parse_programs.py [--data-dir PATH] [--check-evidence] [--check-urls]` prints
  `PROBLEM <program_id> <field>: <message>` for each rule broken, `UNCONFIRMED` lines for
  fields marked unconfirmed, and a final `SUMMARY programs=<n> problems=<n>`. It exits 1 only
  when there are problems. `--check-evidence` adds `EVIDENCE <FOUND|NOT_FOUND|NO_SNAPSHOT>
  <program_id> <field> <url>` lines and `--check-urls` adds `URL <status> <program_id> <url>`
  lines; both are advisory and never change the exit code.
- `index_to_chromadb.py` and `check_retrieval.py` print `Indexed <n> programs, <m> chunks into
  <dir>` (or `INDEX OK` / `INDEX STALE` with `--check`) and `PASS` / `FAIL` lines plus
  `SUMMARY pass=<n> fail=<n>`.

## Field conventions

Every record has exactly the keys of `Program` and `Eligibility` in `backend/models/program.py`,
in that order, with nulls and `false` written out. Files are UTF-8,
`json.dumps(indent=2, ensure_ascii=False)`, with a trailing newline.

- `program_id`: lowercase snake case, unique, ending `_federal` in `federal_programs.json` and
  `_tx` in `texas_programs.json`. `category`: nutrition, health, cash, disability, energy or employment.
- `description`: 60 to 180 words, plain language, paraphrased. The first sentence stands alone on a
  card. Cover who qualifies, what it provides and the caveats the source states. No advice or promises.
- `income_limit_pct_fpl`: set only when an official page states the limit as a percent of the
  federal poverty level; never back-calculate it from a dollar table. If limits differ by group, use
  the highest and list every band in `description`. `null` when there is no percent test.
- `citizenship_required`, `age_min`, `age_max`: describe the person who receives the benefit (the child
  for a children's program), not the adult filling in the quiz. Ages are inclusive whole years
  ("under 19" is `age_max: 18`). `null` when age is only one of several ways to qualify.
- `requires_children`, `requires_disability`, `requires_pregnancy`: `true` only if required on every
  path to eligibility. When the rule is "A or B", leave them unset and say so in `description`.
- `estimated_monthly_value_usd`: only an average or typical benefit the agency publishes. Otherwise `null`.
- `application_url`: https, on an official host, never `benefits.gov`, a stable landing page.
  Allowed hosts are any `.gov` host plus `yourtexasbenefits.com` and `texaswic.org`.
- `processing_time_days`: the upper bound the source states, 1 to 730, else `null`.
- `last_updated`: the ISO date the record was verified. No em dash characters anywhere.

## Sidecar format

`data/sources/federal_sources.json` and `texas_sources.json` are one object keyed by `program_id`:

```json
{
  "example_program_tx": {
    "verified_on": "YYYY-MM-DD",
    "figures_effective": "the period the figures apply to, as the source states it",
    "fields": {
      "description": {"urls": ["https://..."], "evidence": "", "note": ""},
      "eligibility.income_limit_pct_fpl": {"urls": ["https://..."], "evidence": "verbatim snippet, 15 words or fewer", "note": ""},
      "application_url": {"urls": ["https://..."], "evidence": "HTTP 200 on YYYY-MM-DD", "note": "method: http or browser"}
    }
  }
}
```

Required in `fields`: `description`, `eligibility.citizenship_required`, `application_url`; each
non-null `income_limit_pct_fpl`, `age_min`, `age_max`, `estimated_monthly_value_usd` and
`processing_time_days`; each `requires_*` that is true; and `documents_needed` when not empty. Every
entry needs at least one https official URL, and numeric and boolean fields need non-empty `evidence`.
`"unconfirmed": true` is allowed only on boolean eligibility fields; it is listed in the output.

## When figures change each year

- SNAP maximums and income standards: October 1 (new federal fiscal year).
- HHS poverty guidelines: January.
- WIC income guidelines: July 1.
- Medicare and SSA figures: January.

After a change, re-verify against the official page, update the record and its sidecar entry, and run
the pipeline again.

## Generated files

`data/raw/` (page snapshots and `fetch_log.json`) and `data/chroma_db/` (the vector index) are generated by
these scripts and gitignored. Rebuild them rather than committing them.
