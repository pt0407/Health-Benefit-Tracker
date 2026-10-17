# Component 2: The Quiz — Screening Question Design & Integration Schema

**Owner:** Laksh  
**Status:** Draft v1.0 — October 16, 2026  
**Programs in scope:** SNAP, Medicaid, CHIP, LIHEAP, WIC  
**Consumers of this component's output:** Component 1 (Knowledge Base — Surya), Component 3 (Insurance Coverage Agent — Sai Sams), Component 4 (RAG Engine — Pranav)

---

## 1. Purpose & Scope

The Quiz is the single intake point for the app. It collects the minimum set of facts needed to route a household into every major eligibility pathway for the five programs above, then emits one standardized JSON payload (`quiz_response_payload.json`) that the other three components consume.

**What the Quiz does:**
- Asks 12 questions (11 always shown, 1 conditional) in plain language.
- Validates and normalizes answers (e.g., converts weekly pay to monthly).
- Computes a small set of *derived, rule-neutral* fields (household size, age brackets, monthly totals).
- Emits pre-screening flags that tell downstream components which pathways to evaluate.

**What the Quiz does NOT do:**
- It does not make final eligibility decisions. Thresholds and state-specific rules are owned by Component 1; health coverage determinations by Component 3; document retrieval and PDF mapping by Component 4.
- It does not collect names, SSNs, dates of birth or addresses. Those are only needed at PDF pre-fill time and should be gathered in a separate, opt-in step owned by Component 4.

---

## 2. Research Summary: Policy Triggers the Quiz Must Capture

All figures are for the 48 contiguous states + DC. Alaska and Hawaii use higher tables, which is one reason the state is the first question. Component 1 remains the authoritative source for live values; the numbers here justify *why* each question exists.

### 2.1 Federal Poverty Guidelines (2026)
- HHS published the 2026 guidelines January 15, 2026: **$15,960** for 1 person, **$33,000** for 4, **+$5,680** per additional person.
- Each program decides which FPL multiple it uses, what income counts, and how the household is defined — so the Quiz must capture raw ingredients, not a single "income test."

| Program | Income test | Household unit |
|---|---|---|
| SNAP | Gross ≤ 130% FPL; Net ≤ 100% FPL (FY2027, effective Oct 1, 2026) | People who buy and prepare food together |
| Medicaid (expansion adults) | MAGI ≤ 138% FPL (only in expansion states) | Tax-filing household |
| Medicaid/CHIP (children & pregnancy) | State-set; pregnancy national median 201% Medicaid / 258% CHIP (Jan 2026) | Tax household; pregnant woman counts herself + expected babies |
| WIC | Gross ≤ 185% FPL (July 1, 2026 – June 30, 2027), or adjunctive eligibility | Economic unit; pregnant woman counts expected babies |
| LIHEAP | State sets limit between 110% FPL and the greater of 150% FPL or 60% State Median Income | Household sharing the energy bill |

### 2.2 SNAP (FY2027 values, effective October 1, 2026)
- **Gross limit (130% FPL):** $1,729/mo (1 person) … $3,575/mo (4 people), +$616 per person.
- **Net limit (100% FPL):** $1,330/mo (1) … $2,750/mo (4).
- **Deductions that create eligibility:** 20% earned income deduction; standard deduction ($217 for 1–3 people, $229 for 4, $268 for 5, $308 for 6+); dependent care (no cap); medical expenses over $35/mo for elderly (60+) or disabled members; legally owed child support paid; excess shelter deduction (housing + utilities above 50% of adjusted income, capped at **$769**, uncapped if a member is elderly or disabled).
- **Elderly/disabled households** skip the gross test (net test only), get the uncapped shelter deduction, and have a **$4,750** resource limit vs **$3,000** for others.
- **Broad-Based Categorical Eligibility (BBCE):** many states raise the gross limit (up to 200% FPL) and waive the asset test. This is why the asset question is conditional on state.
- **One Big Beautiful Bill Act (OBBBA, P.L. 119-21, July 4, 2025) changes:**
  - ABAWD time limit (3 months in 36 unless 80 hrs/month of work/training) now applies to ages **18–64** (was 18–54).
  - Parent exemption narrowed to households with a child **under 14** (was under 18).
  - Exemptions **removed** for veterans, people experiencing homelessness, and former foster youth ≤ 24; exemption **added** for American Indians/Alaska Natives.
  - Noncitizen eligibility narrowed to U.S. citizens/nationals, lawful permanent residents (LPRs), Cuban/Haitian entrants, and COFA citizens; refugees and asylees who have not adjusted to LPR are no longer eligible by that status. (Implementation details are subject to ongoing multi-state litigation — Component 1 should track the live rule.)

### 2.3 Medicaid & CHIP
- **Expansion adults:** MAGI ≤ 138% FPL in expansion states only.
- **OBBBA community-engagement requirement:** starting **January 1, 2027** (some states earlier — Nebraska began May 1, 2026; Arkansas soft-launched July 1, 2026), expansion adults aged **19–64** must show **80 hours/month** of work, community service, work program or education, *or* monthly income ≥ minimum wage × 80 hours (**$580**). Exemptions include pregnant/postpartum women, people with disabilities/medically frail, and parents/caretakers of young children.
- **Pregnancy and children:** limits are much higher than for adults and vary widely by state (e.g., pregnancy Medicaid from 138% in Idaho to 324% in DC).
- **CHIP** covers uninsured children under 19 above Medicaid limits — so the Quiz must know whether a child already has coverage.

### 2.4 WIC (July 1, 2026 – June 30, 2027)
- Categorical groups: pregnant women; postpartum women (up to 6 months, or 12 if breastfeeding); infants; children **under 5**.
- Income ≤ 185% FPL: **$29,526**/yr (1) … **$61,050**/yr (4), +$10,508 per person.
- **Adjunctive eligibility:** a person receiving Medicaid, SNAP or TANF is automatically income-eligible (some states add CHIP).
- Nutritional risk is assessed in-clinic and is out of scope for a screener.

### 2.5 LIHEAP
- Statutory maximum is the greater of **150% FPL** or **60% of State Median Income (SMI)**; states may not set limits below **110% FPL**.
- Most states grant **categorical eligibility** to households receiving SNAP, SSI or TANF.
- Priority groups: households with young children, members 60+, or members with disabilities, and households with a high energy burden.

---

## 3. Question Specifications

Conventions:
- `field` = the key written into the payload.
- Monetary inputs are integers in **whole U.S. dollars**.
- Every question supports a "Not sure" path where noted; unsure answers produce a `needs_review` flag rather than blocking the user.
- **Frequency normalization** (follows SNAP conversion convention at 7 CFR 273.10(c)(2)): weekly × 4.3, every two weeks × 2.15, twice a month × 2, monthly × 1, yearly ÷ 12. Results are rounded down to whole dollars.

---

### Q1. Location
**Prompt:** "What state do you live in, and what's your ZIP code?"

| Attribute | Spec |
|---|---|
| Fields | `location.state_code`, `location.zip_code` |
| Input type | Dropdown (50 states + DC + territories); 5-digit text input |
| Validation | `state_code` ∈ USPS two-letter codes (required). `zip_code` matches `^\d{5}$` (optional but recommended). If ZIP is given, check it falls within the selected state (lookup via Component 1); on mismatch, prompt to confirm. |
| Feeds | Component 1 (primary key for all rule lookups), Component 4 (state-specific forms) |

**Policy justification:**
- **Every** program is state-administered. State determines: Medicaid expansion status (the 138% adult pathway exists only in expansion states), CHIP and pregnancy limits, SNAP BBCE rules (gross limit up to 200% FPL and asset waiver), LIHEAP thresholds (anywhere from 110% FPL to 60% SMI) and application seasons.
- Alaska and Hawaii use separate, higher FPL tables.
- ZIP lets Component 1/4 route to the correct county office, LIHEAP local agency or WIC clinic, and supports SNAP Standard Utility Allowances that vary by region in some states.

---

### Q2. Household Members
**Prompt:** "Who lives with you? Add yourself first, then everyone else in your home."  
For each person: *age*, *relationship to you*, *"Do you buy and cook food together?"*, *"Will you claim this person as a dependent on your taxes?"*

| Attribute | Spec |
|---|---|
| Fields | `household.members[]` → `member_id`, `age_years`, `relationship`, `shares_food`, `tax_dependent` |
| Input type | Repeater card (1–20 rows). Age: integer stepper. Relationship: enum `self`, `spouse`, `partner`, `child`, `parent`, `sibling`, `grandchild`, `other_relative`, `non_relative`. Booleans: Yes/No toggles. |
| Validation | Exactly one `self`. `age_years` integer 0–120; for infants, "Under 1" maps to `0`. At most one `spouse`/`partner`. `self` must be ≥ 14 (else show "Ask a parent or guardian to complete this quiz"). Max 20 members. |
| Derived | `snap_household_size` (members with `shares_food = true`), `tax_household_size` (self + spouse + tax dependents), `age_brackets` per member |
| Feeds | All three components |

**Policy justification:**
- **Household size is the denominator for every FPL test.** Programs define households differently: SNAP counts people who buy and prepare food together; Medicaid/CHIP use tax-filing relationships. Capturing both booleans lets Components 1 and 3 build their own units from one roster.
- **Age is the single most important trigger after income:**
  - `< 1` and `< 5` → WIC infant/child categories.
  - `< 14` → SNAP ABAWD exemption for the household (post-OBBBA) and Medicaid work-requirement caretaker exemption.
  - `< 19` → CHIP / children's Medicaid.
  - `18–64` → SNAP ABAWD time limit applies (OBBBA raised the upper age from 54 to 64).
  - `19–64` → Medicaid expansion and the 2027 community-engagement requirement.
  - `60+` → SNAP "elderly": net-income test only, uncapped shelter deduction, $35+ medical deduction, $4,750 asset limit; LIHEAP priority group.
  - `65+` → ABAWD exempt; Medicare/Medicaid dual pathway (Component 3).
- Age (not DOB) is collected to minimize PII; Component 4 collects DOB only at PDF time.

---

### Q3. Pregnancy & New Parents
**Prompt:** "Is anyone in your home pregnant, or did anyone give birth in the last 12 months?"  
If pregnant: "How many babies are expected?" If gave birth: "How many months ago?" and "Are you breastfeeding?"

| Attribute | Spec |
|---|---|
| Fields | `household.members[].pregnancy = { is_pregnant, expected_babies, months_postpartum, is_breastfeeding }` |
| Input type | Member picker (only members aged 10–60 shown) → Yes/No toggles; `expected_babies` stepper 1–4 (default 1); `months_postpartum` 0–12 |
| Validation | `is_pregnant` and `months_postpartum` may both be set (rare but valid). `expected_babies` required if `is_pregnant = true`. `is_breastfeeding` only shown if `months_postpartum` is set. |
| Derived | `medicaid_household_size_pregnancy_adjusted` = `tax_household_size` + (`expected_babies` for each pregnant member) |
| Feeds | Component 1 (WIC, SNAP), Component 3 (pregnancy Medicaid/CHIP, postpartum coverage) |

**Policy justification:**
- **WIC categorical eligibility:** pregnant women and postpartum women (6 months, or 12 if breastfeeding) are core WIC categories; without this question the app can never match WIC for adults.
- **Medicaid/CHIP pregnancy pathways** have far higher income limits than adult coverage (national median 201% Medicaid / 258% CHIP vs 138% for expansion adults), and a pregnant woman is counted as herself plus her expected babies when sizing the household. A family of 2 with twins on the way is tested as a household of 4.
- **Postpartum coverage** extends Medicaid eligibility after birth in most states.
- **Medicaid work requirement:** pregnant and postpartum women are exempt.

---

### Q4. Disability & Health Conditions
**Prompt:** "Does anyone in your home have a disability or a health condition that limits their ability to work? Include anyone who gets SSI, SSDI, or VA disability benefits."

| Attribute | Spec |
|---|---|
| Fields | `household.members[].disability = { has_disability, receives_disability_benefit: enum[ssi, ssdi, va_disability, state_disability, none] }` |
| Input type | Member picker → Yes/No → multi-select for benefit source |
| Validation | If `receives_disability_benefit` ≠ `none`, force `has_disability = true`. |
| Feeds | Component 1 (SNAP rules), Component 3 (non-MAGI / disability Medicaid, medically frail exemption) |

**Policy justification:**
- **SNAP:** a household with a disabled member (generally defined by receipt of disability benefits such as SSI/SSDI) gets the same advantages as elderly households — net test only, uncapped shelter deduction, medical expense deduction over $35/mo, $4,750 asset limit — and the member is exempt from ABAWD rules.
- **Medicaid:** disability opens non-MAGI pathways (SSI-linked Medicaid in most states) and is an exemption from the 2027 work requirement.
- **LIHEAP:** members with disabilities are a federal priority group.

---

### Q5. Household Income
**Prompt:** "How much money does your household get before taxes? Add each source."  
Source types: *Job wages*, *Self-employment*, *Social Security/SSI/SSDI*, *Unemployment*, *Child support received*, *Pension/retirement*, *Other*.

| Attribute | Spec |
|---|---|
| Fields | `income.sources[] = { member_id, type, amount, frequency, monthly_amount }`; derived `income.gross_monthly_earned`, `income.gross_monthly_unearned`, `income.gross_monthly_total`, `income.annualized_total` |
| Input type | Repeater: member picker, enum `type`, currency input, frequency enum (`weekly`, `biweekly`, `semimonthly`, `monthly`, `yearly`) |
| Validation | `amount` integer 0–1,000,000. "No income" checkbox allowed (sets total to 0 with `income.reported_zero = true`). Soft warning if `gross_monthly_total` > 400% FPL for household size ("Please double-check"). Self-employment collects **net** profit (after business expenses) with a helper tip. |
| Earned vs. unearned | Earned = `wages`, `self_employment`. Unearned = all others. |
| Feeds | Component 1 (SNAP, WIC, LIHEAP tests), Component 3 (MAGI, CHIP, work-req income equivalence) |

**Policy justification:**
- Income is the core test for all five programs: SNAP gross 130% / net 100%, Medicaid adult 138%, WIC 185%, LIHEAP 150% or 60% SMI, CHIP state-set.
- **Earned vs. unearned split is required** because SNAP excludes 20% of earned income only.
- **Per-member attribution is required** for the Medicaid work requirement, which can be satisfied by an individual earning at least $580/month (federal minimum wage × 80 hours), and for MAGI calculations where a dependent child's income may not count.
- **Child support received** counts as unearned income for SNAP; tracked separately so Component 3 can apply MAGI rules (where it is excluded).
- Normalizing frequency up front prevents the most common screener error: comparing biweekly pay to a monthly limit.

---

### Q6. Current Benefits
**Prompt:** "Does anyone in your home already get any of these?"  
Options: *SNAP (food stamps)*, *TANF (cash assistance)*, *SSI*, *Medicaid*, *CHIP*, *WIC*, *LIHEAP (energy help)*, *Housing assistance (Section 8/public housing)*, *None of these*.

| Attribute | Spec |
|---|---|
| Fields | `current_benefits[] = { program, member_ids[] }` |
| Input type | Multi-select checkboxes → for each selection, member picker ("Who gets it?") with "Everyone" shortcut |
| Validation | "None of these" is mutually exclusive. |
| Feeds | Component 1 (categorical eligibility), Component 3 (existing coverage), Component 4 (skip redundant forms) |

**Policy justification:** this single question unlocks every **categorical / adjunctive eligibility** shortcut:
- **WIC:** current Medicaid, SNAP or TANF recipients are automatically income-eligible.
- **LIHEAP:** most states treat SNAP, SSI or TANF households as categorically eligible.
- **SNAP:** TANF/SSI recipients are often categorically eligible; BBCE extends this.
- **Medicaid work requirement:** many states treat SNAP/TANF participants who are meeting those programs' work rules as compliant.
- It also prevents recommending a program the household already receives and tells Component 4 which forms are renewals vs. new applications.

---

### Q7. Housing & Utility Costs
**Prompt:** "What does your household pay each month for housing and utilities?"

| Sub-field | Field | Input type |
|---|---|---|
| Rent or mortgage payment | `expenses.housing.rent_or_mortgage_monthly` | Currency |
| Property tax + homeowners insurance (if not in mortgage) | `expenses.housing.tax_insurance_monthly` | Currency (optional) |
| Do you pay for heating or cooling separately from rent? | `expenses.utilities.pays_heating_cooling` | Yes/No |
| Main heating fuel | `expenses.utilities.heating_fuel` | Enum: `natural_gas`, `electricity`, `propane`, `fuel_oil`, `wood`, `other`, `included_in_rent` |
| Average monthly energy bill | `expenses.utilities.energy_monthly` | Currency (optional, "Not sure" allowed) |
| Have you received a shut-off notice or are you out of fuel? | `expenses.utilities.energy_crisis` | Yes/No |
| Housing situation | `expenses.housing.situation` | Enum: `rent`, `own`, `live_with_others_free`, `shelter`, `no_stable_housing` |

| Attribute | Spec |
|---|---|
| Validation | Currency 0–20,000. If `situation = own` or `rent`, `rent_or_mortgage_monthly` is required (0 allowed with confirmation). If `heating_fuel = included_in_rent`, force `pays_heating_cooling = false`. |
| Feeds | Component 1 (SNAP shelter deduction, LIHEAP), Component 4 (LIHEAP crisis forms) |

**Policy justification:**
- **SNAP excess shelter deduction** is the deduction that most often moves a household under the net limit: housing + utilities above 50% of adjusted income are deducted, capped at $769 (uncapped for elderly/disabled households). States usually apply a **Standard Utility Allowance (SUA)** rather than actual bills — and qualifying for the SUA typically hinges on whether the household pays heating/cooling separately, which is why that yes/no is mandatory but the dollar amount is optional.
- **LIHEAP** targets heating/cooling costs; fuel type affects benefit levels and vendor payment, energy burden is a priority factor, and a shut-off notice triggers the **crisis** component.
- **Homeless households** may receive a separate SNAP homeless shelter deduction; capturing `shelter`/`no_stable_housing` routes this.

---

### Q8. Other Monthly Expenses
**Prompt:** "Does your household pay for any of these each month?"

| Sub-field | Field | Shown when |
|---|---|---|
| Child care or adult dependent care (so someone can work, look for work, or go to school) | `expenses.dependent_care_monthly` | Always |
| Court-ordered child support you pay | `expenses.child_support_paid_monthly` | Always |
| Out-of-pocket medical costs (prescriptions, copays, insurance premiums, transportation to care) | `expenses.medical_out_of_pocket_monthly` | Only if any member is 60+ or has a disability |

| Attribute | Spec |
|---|---|
| Input type | Currency inputs with "None" shortcut |
| Validation | 0–20,000 each. |
| Feeds | Component 1 (SNAP net income) |

**Policy justification:** these map one-to-one to SNAP's remaining allowable deductions — dependent care (no cap), legally owed child support paid, and medical expenses over $35/month for elderly or disabled members. Conditional display of the medical field keeps the quiz short for households where it can't apply.

---

### Q9. Work, School & Training Hours
**Prompt (per adult aged 18–64):** "About how many hours a week does this person usually spend working, in school or job training, or volunteering?"

| Attribute | Spec |
|---|---|
| Fields | `household.members[].activity = { work_hours_weekly, school_or_training_hours_weekly, volunteer_hours_weekly, is_american_indian_alaska_native }` |
| Input type | Integer steppers 0–80 per category; AI/AN as Yes/No/"Prefer not to say" |
| Validation | Sum ≤ 112 hrs/week. Only shown for members aged 18–64. |
| Derived | `monthly_engagement_hours` = sum × 4.3 (rounded down) |
| Feeds | Component 1 (SNAP ABAWD), Component 3 (Medicaid community engagement) |

**Policy justification:**
- **SNAP ABAWD rule (post-OBBBA):** adults 18–64 without a child under 14 and without another exemption are limited to 3 months of SNAP in 36 unless they meet 80 hours/month of work or qualifying activity. American Indians/Alaska Natives are now exempt; veterans, people experiencing homelessness and former foster youth no longer are.
- **Medicaid community engagement (Jan 1, 2027):** expansion adults 19–64 need 80 hours/month of work, community service, work program or education — or the $580/month income equivalent from Q5.
- Collecting weekly hours (what people actually know) and converting to monthly lets both components apply the 80-hour threshold.
- This question is presented as informational: a low-hour answer **never** removes a program from results; it adds a `work_requirement_review` flag so users learn about exemptions and E&T options.

---

### Q10. Citizenship & Immigration Status
**Prompt (per member):** "Which best describes this person?"  
Options: *U.S. citizen or national*, *Green card holder (lawful permanent resident)*, *Refugee or asylee*, *Other lawful status (visa, parole, TPS, COFA, etc.)*, *Prefer not to say*.  
Follow-up (green card holders only): "Has this person had a green card for 5 years or more?"

| Attribute | Spec |
|---|---|
| Fields | `household.members[].immigration = { category, lpr_5_years_plus }` |
| Input type | Radio per member; Yes/No/"Not sure" follow-up |
| Validation | Defaults to `prefer_not_to_say` if skipped. Never required. |
| Privacy | Show the notice: "We don't share this. Many programs let citizen children get benefits even if a parent doesn't qualify." Store category only — never document numbers. |
| Feeds | Component 1 (SNAP), Component 3 (Medicaid/CHIP lawful-presence rules) |

**Policy justification:**
- **SNAP (OBBBA):** eligibility is now limited to citizens/nationals, LPRs (generally after a 5-year wait unless exempt), Cuban/Haitian entrants and COFA citizens; refugees and asylees are no longer eligible by that status alone. Because parts of the implementation are in litigation, Component 1 should apply the live rule.
- **Medicaid/CHIP:** most lawfully present immigrants face a 5-year bar, but many states use the option to cover lawfully residing children and pregnant women without the wait.
- **Mixed-status households:** ineligible members are excluded from the benefit unit but their income may still count. Per-member status lets citizen children be screened correctly instead of the whole household being turned away.
- "Prefer not to say" is essential for trust and completion rates; it produces a `needs_review` flag, not an exclusion.

---

### Q11. Current Health Coverage
**Prompt (per member):** "Does this person have health insurance right now?"  
Options: *No insurance*, *Through a job*, *Marketplace (Healthcare.gov) plan*, *Medicaid*, *CHIP*, *Medicare*, *Military/VA/TRICARE*, *Other*, *Not sure*.  
Follow-up for job-based: "Does the job offer coverage for the whole family?"

| Attribute | Spec |
|---|---|
| Fields | `household.members[].health_coverage = { source, employer_offers_family_coverage }` |
| Input type | Dropdown per member; Yes/No/"Not sure" follow-up |
| Feeds | Component 3 (primary), Component 1 |

**Policy justification:**
- **CHIP is for uninsured children** — states generally deny CHIP to children who have other comprehensive coverage, so Component 3 cannot evaluate CHIP without this.
- **Medicare (65+ or disabled)** routes to dual-eligible / Medicare Savings Program logic instead of MAGI Medicaid.
- **Employer family coverage** affects Marketplace subsidy eligibility and is the other half of the coverage picture Component 3 evaluates.
- Existing Medicaid also triggers WIC adjunctive eligibility (cross-referenced with Q6).

---

### Q12 (Conditional). Savings & Resources
**Shown only when** Component 1 returns `state_rules.snap_asset_test_applies = true` (i.e., the state does not use BBCE to waive the SNAP resource test).

**Prompt:** "About how much does your household have in cash, checking and savings accounts combined?"

| Attribute | Spec |
|---|---|
| Fields | `resources.liquid_assets_band` |
| Input type | Banded radio: `under_3000`, `3000_to_4750`, `over_4750`, `not_sure` |
| Validation | Required when shown. |
| Feeds | Component 1 |

**Policy justification:** SNAP's federal resource limits are $3,000, or $4,750 for households with an elderly or disabled member. Bands aligned to those two limits give Component 1 everything it needs without asking for an exact balance. Medicaid MAGI, CHIP, WIC and most LIHEAP programs have no asset test, which is why this question is hidden in the majority of states.

---

## 4. Question → Program Coverage Matrix

| # | Question | SNAP | Medicaid | CHIP | LIHEAP | WIC |
|---|---|:-:|:-:|:-:|:-:|:-:|
| 1 | Location | ● | ● | ● | ● | ● |
| 2 | Household members & ages | ● | ● | ● | ● | ● |
| 3 | Pregnancy / postpartum | ○ | ● | ● | ○ | ● |
| 4 | Disability | ● | ● | ○ | ● | |
| 5 | Income | ● | ● | ● | ● | ● |
| 6 | Current benefits | ● | ● | ○ | ● | ● |
| 7 | Housing & utilities | ● | | | ● | |
| 8 | Other expenses | ● | | | | |
| 9 | Work/activity hours | ● | ● | | | |
| 10 | Immigration status | ● | ● | ● | ○ | |
| 11 | Health coverage | | ● | ● | | ○ |
| 12 | Resources (conditional) | ● | | | | |

● primary trigger ○ secondary / priority factor

**Estimated completion time:** 4–6 minutes for a household of 4.

---

## 5. Flow & Branching Logic

```
Q1 Location ──► call Component 1: GET /state-rules/{state_code}
     │              (returns snap_asset_test_applies, medicaid_expansion, etc.)
Q2 Household roster
     │
     ├─ any member age 10–60? ─────────► Q3 Pregnancy
Q4 Disability
Q5 Income
Q6 Current benefits
Q7 Housing & utilities
Q8 Other expenses (medical field only if 60+ or disabled)
     │
     ├─ any member age 18–64? ─────────► Q9 Work/activity hours
Q10 Immigration status
Q11 Health coverage
     │
     ├─ snap_asset_test_applies? ──────► Q12 Resources
     ▼
Review screen (editable summary) ──► emit quiz_response_payload.json
```

UX requirements:
- Progress bar; back navigation preserves answers.
- Reading level target: grade 6–8. Spanish translation planned for v1.1.
- Accessibility: WCAG 2.1 AA (labels on all inputs, keyboard navigation, no color-only cues).
- No answer except Q1 state, Q2 roster and Q5 income is hard-required; skipped items emit `needs_review` flags.

---

## 6. Integration: `quiz_response_payload.json`

### 6.1 Design principles
1. **One canonical payload** — no per-consumer copies of data. Each component reads the paths it needs (see routing map, §6.4).
2. **Raw + normalized** — store the user's original amount/frequency *and* the monthly figure, so Component 4 can pre-fill forms that ask for pay-period amounts.
3. **Rule-neutral** — the Quiz never writes eligibility outcomes; `screening_flags` only say *which pathways to evaluate*.
4. **Versioned** — `schema_version` uses semver; breaking changes bump the major version.
5. **Minimal PII** — no names, DOB, SSN or street address.

### 6.2 JSON Schema (Draft 2020-12)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/schemas/quiz_response_payload.schema.json",
  "title": "QuizResponsePayload",
  "type": "object",
  "required": ["schema_version", "session", "location", "household", "income"],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0.0" },

    "session": {
      "type": "object",
      "required": ["session_id", "completed_at", "locale"],
      "properties": {
        "session_id": { "type": "string", "format": "uuid" },
        "completed_at": { "type": "string", "format": "date-time" },
        "locale": { "type": "string", "enum": ["en-US", "es-US"] },
        "fpl_table_year": { "type": "integer", "examples": [2026] }
      }
    },

    "location": {
      "type": "object",
      "required": ["state_code"],
      "properties": {
        "state_code": { "type": "string", "pattern": "^[A-Z]{2}$" },
        "zip_code": { "type": ["string", "null"], "pattern": "^\\d{5}$" }
      }
    },

    "household": {
      "type": "object",
      "required": ["members"],
      "properties": {
        "members": {
          "type": "array",
          "minItems": 1,
          "maxItems": 20,
          "items": { "$ref": "#/$defs/member" }
        },
        "derived": {
          "type": "object",
          "properties": {
            "total_members": { "type": "integer" },
            "snap_household_size": { "type": "integer" },
            "tax_household_size": { "type": "integer" },
            "medicaid_household_size_pregnancy_adjusted": { "type": "integer" },
            "has_member_under_1": { "type": "boolean" },
            "has_member_under_5": { "type": "boolean" },
            "has_member_under_14": { "type": "boolean" },
            "has_member_under_19": { "type": "boolean" },
            "has_member_60_plus": { "type": "boolean" },
            "has_member_with_disability": { "type": "boolean" },
            "has_pregnant_or_postpartum_member": { "type": "boolean" }
          }
        }
      }
    },

    "income": {
      "type": "object",
      "required": ["sources", "gross_monthly_total"],
      "properties": {
        "reported_zero": { "type": "boolean" },
        "sources": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["member_id", "type", "amount", "frequency", "monthly_amount"],
            "properties": {
              "member_id": { "type": "string" },
              "type": {
                "type": "string",
                "enum": ["wages", "self_employment", "social_security", "ssi", "ssdi",
                         "unemployment", "child_support_received", "pension", "other"]
              },
              "is_earned": { "type": "boolean" },
              "amount": { "type": "integer", "minimum": 0 },
              "frequency": {
                "type": "string",
                "enum": ["weekly", "biweekly", "semimonthly", "monthly", "yearly"]
              },
              "monthly_amount": { "type": "integer", "minimum": 0 }
            }
          }
        },
        "gross_monthly_earned": { "type": "integer" },
        "gross_monthly_unearned": { "type": "integer" },
        "gross_monthly_total": { "type": "integer" },
        "annualized_total": { "type": "integer" }
      }
    },

    "expenses": {
      "type": "object",
      "properties": {
        "housing": {
          "type": "object",
          "properties": {
            "situation": {
              "type": "string",
              "enum": ["rent", "own", "live_with_others_free", "shelter", "no_stable_housing"]
            },
            "rent_or_mortgage_monthly": { "type": ["integer", "null"] },
            "tax_insurance_monthly": { "type": ["integer", "null"] }
          }
        },
        "utilities": {
          "type": "object",
          "properties": {
            "pays_heating_cooling": { "type": ["boolean", "null"] },
            "heating_fuel": {
              "type": ["string", "null"],
              "enum": ["natural_gas", "electricity", "propane", "fuel_oil", "wood",
                       "other", "included_in_rent", null]
            },
            "energy_monthly": { "type": ["integer", "null"] },
            "energy_crisis": { "type": ["boolean", "null"] }
          }
        },
        "dependent_care_monthly": { "type": ["integer", "null"] },
        "child_support_paid_monthly": { "type": ["integer", "null"] },
        "medical_out_of_pocket_monthly": { "type": ["integer", "null"] }
      }
    },

    "current_benefits": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["program", "member_ids"],
        "properties": {
          "program": {
            "type": "string",
            "enum": ["snap", "tanf", "ssi", "medicaid", "chip", "wic", "liheap", "housing_assistance"]
          },
          "member_ids": { "type": "array", "items": { "type": "string" } }
        }
      }
    },

    "resources": {
      "type": ["object", "null"],
      "properties": {
        "asked": { "type": "boolean" },
        "liquid_assets_band": {
          "type": ["string", "null"],
          "enum": ["under_3000", "3000_to_4750", "over_4750", "not_sure", null]
        }
      }
    },

    "screening_flags": {
      "type": "object",
      "description": "Pathways to evaluate. NOT eligibility decisions.",
      "properties": {
        "evaluate_programs": {
          "type": "array",
          "items": { "type": "string", "enum": ["snap", "medicaid", "chip", "liheap", "wic"] }
        },
        "pathways": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "snap_elderly_disabled_rules",
              "snap_abawd_review",
              "snap_shelter_deduction",
              "snap_homeless_shelter_deduction",
              "snap_categorical_tanf_ssi",
              "medicaid_expansion_adult",
              "medicaid_pregnancy",
              "medicaid_postpartum",
              "medicaid_child",
              "medicaid_disability_non_magi",
              "medicaid_work_requirement_review",
              "chip_child",
              "wic_categorical_pregnant",
              "wic_categorical_postpartum",
              "wic_categorical_infant_child",
              "wic_adjunctive_income",
              "liheap_categorical",
              "liheap_priority_household",
              "liheap_crisis",
              "medicare_dual_review"
            ]
          }
        },
        "needs_review": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "field": { "type": "string" },
              "reason": { "type": "string", "enum": ["skipped", "not_sure", "prefer_not_to_say", "soft_validation_warning"] }
            }
          }
        }
      }
    },

    "rag_context": {
      "type": "object",
      "description": "Pre-built context for Component 4.",
      "properties": {
        "household_summary": { "type": "string", "maxLength": 1200 },
        "retrieval_keys": {
          "type": "array",
          "items": { "type": "string" },
          "description": "e.g. ['TX', 'snap', 'wic', 'pregnancy', 'chip']"
        }
      }
    }
  },

  "$defs": {
    "member": {
      "type": "object",
      "required": ["member_id", "age_years", "relationship"],
      "properties": {
        "member_id": { "type": "string", "pattern": "^m[0-9]{1,2}$" },
        "age_years": { "type": "integer", "minimum": 0, "maximum": 120 },
        "relationship": {
          "type": "string",
          "enum": ["self", "spouse", "partner", "child", "parent", "sibling",
                   "grandchild", "other_relative", "non_relative"]
        },
        "shares_food": { "type": "boolean" },
        "tax_dependent": { "type": ["boolean", "null"] },
        "pregnancy": {
          "type": ["object", "null"],
          "properties": {
            "is_pregnant": { "type": "boolean" },
            "expected_babies": { "type": ["integer", "null"], "minimum": 1, "maximum": 4 },
            "months_postpartum": { "type": ["integer", "null"], "minimum": 0, "maximum": 12 },
            "is_breastfeeding": { "type": ["boolean", "null"] }
          }
        },
        "disability": {
          "type": ["object", "null"],
          "properties": {
            "has_disability": { "type": "boolean" },
            "receives_disability_benefit": {
              "type": "array",
              "items": { "type": "string", "enum": ["ssi", "ssdi", "va_disability", "state_disability", "none"] }
            }
          }
        },
        "activity": {
          "type": ["object", "null"],
          "properties": {
            "work_hours_weekly": { "type": "integer", "minimum": 0, "maximum": 80 },
            "school_or_training_hours_weekly": { "type": "integer", "minimum": 0, "maximum": 80 },
            "volunteer_hours_weekly": { "type": "integer", "minimum": 0, "maximum": 80 },
            "monthly_engagement_hours": { "type": "integer" },
            "is_american_indian_alaska_native": { "type": ["boolean", "null"] }
          }
        },
        "immigration": {
          "type": ["object", "null"],
          "properties": {
            "category": {
              "type": "string",
              "enum": ["citizen_or_national", "lpr", "refugee_or_asylee", "other_lawful", "prefer_not_to_say"]
            },
            "lpr_5_years_plus": { "type": ["boolean", "null"] }
          }
        },
        "health_coverage": {
          "type": ["object", "null"],
          "properties": {
            "source": {
              "type": "string",
              "enum": ["none", "employer", "marketplace", "medicaid", "chip", "medicare",
                       "military_va", "other", "not_sure"]
            },
            "employer_offers_family_coverage": { "type": ["boolean", "null"] }
          }
        },
        "age_bracket_flags": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["under_1", "under_5", "under_14", "under_19", "age_18_64", "age_19_64", "age_60_plus", "age_65_plus"]
          }
        }
      }
    }
  }
}
```

### 6.3 Example payload

A Texas household of 3: a 29-year-old pregnant mother working part-time, her 31-year-old partner, and a 3-year-old.

```json
{
  "schema_version": "1.0.0",
  "session": {
    "session_id": "6b0f6a7e-1c2d-4f3a-9b8e-2a1d3c4e5f60",
    "completed_at": "2026-10-16T19:30:00-05:00",
    "locale": "en-US",
    "fpl_table_year": 2026
  },
  "location": { "state_code": "TX", "zip_code": "78642" },
  "household": {
    "members": [
      {
        "member_id": "m1", "age_years": 29, "relationship": "self",
        "shares_food": true, "tax_dependent": false,
        "pregnancy": { "is_pregnant": true, "expected_babies": 1, "months_postpartum": null, "is_breastfeeding": null },
        "disability": { "has_disability": false, "receives_disability_benefit": ["none"] },
        "activity": { "work_hours_weekly": 20, "school_or_training_hours_weekly": 0, "volunteer_hours_weekly": 0,
                      "monthly_engagement_hours": 86, "is_american_indian_alaska_native": false },
        "immigration": { "category": "citizen_or_national", "lpr_5_years_plus": null },
        "health_coverage": { "source": "none", "employer_offers_family_coverage": null },
        "age_bracket_flags": ["age_18_64", "age_19_64"]
      },
      {
        "member_id": "m2", "age_years": 31, "relationship": "partner",
        "shares_food": true, "tax_dependent": false,
        "pregnancy": null,
        "disability": { "has_disability": false, "receives_disability_benefit": ["none"] },
        "activity": { "work_hours_weekly": 40, "school_or_training_hours_weekly": 0, "volunteer_hours_weekly": 0,
                      "monthly_engagement_hours": 172, "is_american_indian_alaska_native": false },
        "immigration": { "category": "lpr", "lpr_5_years_plus": true },
        "health_coverage": { "source": "employer", "employer_offers_family_coverage": false },
        "age_bracket_flags": ["age_18_64", "age_19_64"]
      },
      {
        "member_id": "m3", "age_years": 3, "relationship": "child",
        "shares_food": true, "tax_dependent": true,
        "pregnancy": null, "disability": null, "activity": null,
        "immigration": { "category": "citizen_or_national", "lpr_5_years_plus": null },
        "health_coverage": { "source": "none", "employer_offers_family_coverage": null },
        "age_bracket_flags": ["under_5", "under_14", "under_19"]
      }
    ],
    "derived": {
      "total_members": 3,
      "snap_household_size": 3,
      "tax_household_size": 2,
      "medicaid_household_size_pregnancy_adjusted": 3,
      "has_member_under_1": false,
      "has_member_under_5": true,
      "has_member_under_14": true,
      "has_member_under_19": true,
      "has_member_60_plus": false,
      "has_member_with_disability": false,
      "has_pregnant_or_postpartum_member": true
    }
  },
  "income": {
    "reported_zero": false,
    "sources": [
      { "member_id": "m1", "type": "wages", "is_earned": true, "amount": 300, "frequency": "weekly", "monthly_amount": 1290 },
      { "member_id": "m2", "type": "wages", "is_earned": true, "amount": 1100, "frequency": "biweekly", "monthly_amount": 2365 }
    ],
    "gross_monthly_earned": 3655,
    "gross_monthly_unearned": 0,
    "gross_monthly_total": 3655,
    "annualized_total": 43860
  },
  "expenses": {
    "housing": { "situation": "rent", "rent_or_mortgage_monthly": 1350, "tax_insurance_monthly": null },
    "utilities": { "pays_heating_cooling": true, "heating_fuel": "electricity", "energy_monthly": 180, "energy_crisis": false },
    "dependent_care_monthly": 400,
    "child_support_paid_monthly": 0,
    "medical_out_of_pocket_monthly": null
  },
  "current_benefits": [],
  "resources": { "asked": false, "liquid_assets_band": null },
  "screening_flags": {
    "evaluate_programs": ["snap", "medicaid", "chip", "liheap", "wic"],
    "pathways": [
      "snap_shelter_deduction",
      "medicaid_pregnancy",
      "medicaid_child",
      "chip_child",
      "wic_categorical_pregnant",
      "wic_categorical_infant_child",
      "liheap_priority_household"
    ],
    "needs_review": []
  },
  "rag_context": {
    "household_summary": "Texas (ZIP 78642) household of 3: adult (29, pregnant, 1 expected baby, uninsured, works ~20 hrs/wk), adult partner (31, LPR 5+ yrs, employer coverage for self only, works ~40 hrs/wk), child (3, uninsured). Gross monthly income $3,655 (all earned). Rent $1,350/mo; pays electric heating/cooling ~$180/mo. Child care $400/mo. No current benefits.",
    "retrieval_keys": ["TX", "snap", "medicaid", "chip", "wic", "liheap", "pregnancy", "child_under_5", "shelter_deduction", "dependent_care"]
  }
}
```

> Note how this family illustrates why both household definitions matter: the SNAP household is 3 (everyone shares food), the tax household is 2 if the partners are unmarried and only `m1` claims the child, and the pregnancy-adjusted Medicaid household for `m1` grows by one. Gross income is ~$3,655/mo — above the SNAP 130% gross limit for 3 ($2,960) unless Texas BBCE rules raise it, but well within WIC's 185% limit for a household of 4 counting the unborn baby. Component 1 resolves those outcomes; the Quiz just supplies the inputs.

### 6.4 Routing map — who reads what

| Payload path | Component 1 (Surya) — Knowledge Base | Component 3 (Sai Sams) — Insurance Agent | Component 4 (Pranav) — RAG / PDF |
|---|:-:|:-:|:-:|
| `location.state_code`, `location.zip_code` | **Primary key** for state rules | State Medicaid/CHIP limits | Form selection, local office lookup |
| `household.members[].age_years`, `age_bracket_flags` | SNAP elderly, ABAWD, WIC ages | Child/adult/65+ pathways | Form pre-fill (age fields) |
| `household.derived.*_household_size` | SNAP & LIHEAP FPL row | MAGI household, pregnancy count | Form pre-fill |
| `members[].pregnancy` | WIC categories | **Pregnancy/postpartum Medicaid & CHIP** | Pregnancy-specific forms |
| `members[].disability` | SNAP elderly/disabled rules | Non-MAGI Medicaid, work-req exemption | Disability attachments |
| `income.*` | SNAP gross/net, WIC, LIHEAP tests | **MAGI, CHIP, $580 work-req equivalence** | Income sections of forms |
| `expenses.*` | **SNAP deductions, LIHEAP** | — | SNAP & LIHEAP expense sections |
| `current_benefits[]` | Categorical/adjunctive eligibility | Existing coverage | Renewal vs. new application |
| `members[].activity` | **SNAP ABAWD** | **Medicaid community engagement** | Work-requirement forms |
| `members[].immigration` | SNAP noncitizen rules | Medicaid/CHIP lawful presence | Status sections (category only) |
| `members[].health_coverage` | WIC adjunctive cross-check | **Primary input: CHIP/Medicaid/Marketplace** | Insurance sections |
| `resources` | SNAP asset test | — | — |
| `screening_flags` | Which rule sets to load | Which coverage pathways to run | Which documents to retrieve |
| `rag_context` | — | — | **Primary input:** prompt context + retrieval keys |

### 6.5 Interface contract

| Direction | Contract |
|---|---|
| Quiz → Component 1 (before Q12) | `GET /state-rules/{state_code}` → must return at minimum `{ "snap_asset_test_applies": bool, "medicaid_expansion": bool, "fpl_region": "contiguous" \| "alaska" \| "hawaii" }`. If the call fails, the Quiz shows Q12 by default (safe fallback). |
| Quiz → all components (on submit) | Publish `quiz_response_payload.json` (validated against the schema in §6.2). Recommended transport: `POST /api/screenings` returning `screening_id`; consumers fetch by ID. |
| Validation | The Quiz must validate the payload against the schema before emitting. Consumers should reject payloads whose `schema_version` major version they do not support. |
| Change management | Field additions → minor version bump. Renames/removals/type changes → major bump with a migration note in this file. All changes go through a PR reviewed by at least one consumer-component owner. |

---

## 7. Privacy & Safety Requirements

- No names, SSNs, dates of birth, street addresses or immigration document numbers in this payload.
- Immigration status is optional, category-only, and never shared outside the app's own components.
- Store payloads encrypted at rest; delete after 30 days unless the user saves their results.
- Results screens must say: "This is a screening estimate, not an official decision. Only your state agency can decide eligibility."

---

## 8. Test Cases (for implementation)

| ID | Scenario | Expected key outputs |
|---|---|---|
| T1 | Single adult, 45, no income, renting, expansion state | `medicaid_expansion_adult`, `snap_abawd_review`, `snap_shelter_deduction` |
| T2 | Single adult, 62, SSDI only | `snap_elderly_disabled_rules`, `medicaid_disability_non_magi`, `liheap_priority_household`; ABAWD **not** flagged (disability exemption) |
| T3 | Household of 4 receiving SNAP, child under 1 | `wic_adjunctive_income`, `wic_categorical_infant_child`, `liheap_categorical` |
| T4 | Pregnant member expecting twins, household of 2 | `medicaid_household_size_pregnancy_adjusted = 4` |
| T5 | Biweekly pay of $1,000 | `monthly_amount = 2150` |
| T6 | Member selects "Prefer not to say" on immigration | Present in `needs_review`; programs **not** removed from `evaluate_programs` |
| T7 | Energy shut-off notice = yes | `liheap_crisis` |
| T8 | Component 1 state-rules call fails | Q12 shown; payload still valid |

---

## 9. Sources

- HHS/ASPE 2026 Poverty Guidelines — https://aspe.hhs.gov/sites/default/files/documents/b1bfa16b20ae9b89d525bc35de7c1643/detailed-guidelines-2026.pdf
- USDA FNS, OBBB ABAWD Exceptions Implementation Memorandum — https://www.fns.usda.gov/snap/obbb-abawd-exemptions-implementation
- USDA FNS, OBBB Alien SNAP Eligibility Q&A #1 — https://www.fns.usda.gov/snap/obbb-alien-eligibility-qas1
- USDA WIC 2026–2027 Income Eligibility Guidelines (Federal Register, Apr. 29, 2026) — https://public-inspection.federalregister.gov/2026-08323.pdf
- USDA WIC IEG policy memo 2026–2027 — https://www.usda.gov/sites/default/files/guidance-documents/wic-ieg2026-2027.pdf
- ACF LIHEAP IM 2018-3 (income eligibility statutory limits) — https://acf.gov/ocs/policy-guidance/liheap-im-2018-3-state-median-income-estimates-optional-use-fy-2018-and
- ACF LIHEAP Q&A (categorical eligibility, 60% SMI vs 150% FPL) — https://acf.gov/ocs/faq/liheap-q-disaster-relief
- KFF, Medicaid and CHIP Income Eligibility Limits for Pregnant Women (Jan. 2026) — https://www.kff.org/affordable-care-act/state-indicator/medicaid-and-chip-income-eligibility-limits-for-pregnant-women-as-a-percent-of-the-federal-poverty-level/
- KFF, Medicaid and CHIP Eligibility Data Collection — https://www.kff.org/statedata/collection/medicaid-and-chip-eligibility-enrollment-and-renewal-policies/
- SNAP FY2027 income limits and deductions (summaries of USDA COLA) — https://grantshubusa.com/blog/snap-income-limits ; https://benefitguide.net/guides/snap-changes-october-1-2026/
- Medicaid work requirements (OBBBA) — https://www.jdsupra.com/legalnews/ready-set-go-implementation-of-medicaid-7212493/ ; https://news.ballotpedia.org/2026/05/05/nebraska-becomes-first-state-to-implement-medicaid-work-requirements-after-passage-of-the-one-big-beautiful-bill-act/ ; https://ensorahealth.com/blog/new-medicaid-work-requirements-explained/
- South Carolina DSS on OBBBA SNAP exemptions removed — https://dss.sc.gov/news/new-federal-snap-work-requirements-take-effect-in-south-carolina
- Immigration Policy Tracking Project, USDA memo & litigation — https://immpolicytracking.org/policies/usda-issues-memo-on-the-implementation-of-snap-eligibility-following-the-one-big-beautiful-bill-act/

> **Maintenance note:** FPL figures update each January; SNAP figures each October 1; WIC each July 1. Component 1 owns these values — this document should only be updated if a rule change requires a *new question or field*.
