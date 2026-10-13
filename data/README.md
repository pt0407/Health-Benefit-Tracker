# Program data (Owner: Person 2)

Teammate-facing guide to `data/`. The scripts and their output lines are described in
`data/scripts/README.md`; this page is the short version plus the traps.

## Folder map

| Path | What it is | Committed |
|---|---|---|
| `data/programs/federal_programs.json` | Federal program records (`program_id` ends `_federal`) | yes |
| `data/programs/texas_programs.json` | Texas program records (`program_id` ends `_tx`) | yes |
| `data/sources/federal_sources.json`, `texas_sources.json` | Per-field sources, evidence and estimate markers, keyed by `program_id` | yes |
| `data/scripts/` | Snapshot, validate, index and retrieval-check scripts | yes |
| `data/raw/` | Snapshots of the cited official pages plus `fetch_log.json` | no, generated |
| `data/chroma_db/` | The vector index the RAG engine reads | no, generated |

## Record fields

Each record has exactly the keys of `Program` and `Eligibility` in `backend/models/program.py`.

- `program_id`, `name`, `type`, `category`: identity. Categories: nutrition, health, cash, disability, energy, employment.
- `description`: 60 to 180 words, plain language. The first sentence stands alone on a card.
- `eligibility.income_limit_pct_fpl`: highest percent of the federal poverty level at which anyone can qualify, or `null`.
- `eligibility.citizenship_required`, `age_min`, `age_max`: describe the person who receives the benefit (the child for a children's program). Ages are inclusive.
- `eligibility.requires_children`, `requires_disability`, `requires_pregnancy`: `true` only when required on every path. All structured fields are read as "all must hold".
- `estimated_monthly_value_usd`: dollars per month, or `null`. May be an estimate (see Traps).
- `application_url`: where a Texas resident starts the application. `documents_needed`: short noun phrases.
- `processing_time_days`: upper bound in calendar days, or `null`. `source`: administering agency. `last_updated`: ISO date of the last verification.

## Commands

Run from the repo root with the backend venv active:

```
python data/scripts/scrape_benefits_data.py            # snapshot cited official pages into data/raw/ (gitignored)
python data/scripts/parse_programs.py --check-evidence # validate records and cross-check figures against snapshots
python data/scripts/index_to_chromadb.py               # rebuild data/chroma_db/ (gitignored) from data/programs/*.json
python data/scripts/check_retrieval.py                 # run the named retrieval expectations
cd backend && pytest
```

## Sidecar format

`data/sources/*_sources.json` is one object per `program_id`, with `verified_on`, `figures_effective`
and `fields`. Each field entry has `urls` (official https pages), `evidence` (verbatim snippet, 15
words or fewer), and `note`.

An estimated or derived value adds `"estimated": true` and an `estimate` object with `method`,
`represents`, `formula` and `inputs` (name, value, unit, period, url, evidence). The validator
recomputes the formula and compares it with the record value. Every null in the three numeric
fields has an entry with `null_reason` (`no_income_test`, `not_applicable` or `no_official_basis`).
The full format is in `data/scripts/README.md`.

Detect an estimate in code:

```python
sidecar[program_id]["fields"][field].get("estimated") is True
```

`python data/scripts/parse_programs.py` prints one `ESTIMATE <program_id> <field> <method> <value>`
line per estimated field. Read the current values and methods from those lines; they are not copied here.

## Traps

- **Banded limits are the highest band.** When limits differ by age or group, the field holds the highest limit at which anyone can qualify; every band is listed in `description`.
- **SNAP uses the Texas gross limit of 165 percent FPL**, not the federal baseline of 130 percent. The description states both.
- **Processing days are calendar days.** Weeks count 7 days and months 30, using the upper bound of a range.
- **Null never means zero.** `null` is "no income test", "not applicable" or "no official basis". Zero is rejected by the validator. Do not apply an income test when the income field is `null`.
- **Some values are estimates.** Check the sidecar marker or the `ESTIMATE` lines before presenting a figure as exact. The description of such a record says "estimate".
- **Health coverage values are government spending per enrollee, not cash** the household receives. Never add them to a household's cash income.
- **Derived percents use a reference household.** For `medicaid_elderly_disabled_tx` it is one person; for `tanf_tx` it is a family of three with one caretaker (one parent, two children). The percent is floored against the 2026 HHS poverty guideline. Other household sizes are in the sidecar `note`.
- **The index is not committed.** After any data change, rebuild `data/chroma_db/` with `python data/scripts/index_to_chromadb.py`; `--check` prints `INDEX STALE` when it is out of date.
- Sources are official pages only (`.gov` hosts except `benefits.gov`, plus `yourtexasbenefits.com` and `texaswic.org`). Never copy figures from `docs/BUILD_PLAN.md` or third-party sites.

## Changing a record

1. Re-read the official page and update the record, its `last_updated`, and the sidecar entry (`verified_on`, `urls`, `evidence`).
2. If the value is derived, add or update the `estimate` marker and make sure the description says "estimate".
3. Run `python data/scripts/parse_programs.py --check-evidence` and fix every `PROBLEM` line.
4. Rebuild the index, run `python data/scripts/check_retrieval.py`, then `cd backend && pytest`.
5. Keep edits inside your lane; the record schema in `backend/models/program.py` is a shared contract.
