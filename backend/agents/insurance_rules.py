"""Baseline health-coverage eligibility rules for Texas.

The agent uses this text as context until the RAG engine (Person 2) can
supply retrieved program text; when RAG context is passed in, it is appended
after these rules. Keep every rule sourced and dated — the agent is told to
use only what is written here.
"""

# Income limits are percentages of the federal poverty level (FPL) for the
# household size, before the 5% income disregard used for MAGI Medicaid.
TX_INSURANCE_RULES = """\
TEXAS HEALTH COVERAGE RULES (source: Texas HHSC, HealthCare.gov, Medicare.gov; reviewed 2026)

Texas has NOT expanded Medicaid under the ACA.
- Adults aged 19-64 who are not pregnant, not disabled and not caring for
  a child generally cannot get Medicaid in Texas at any income.
- Parents/caretaker relatives qualify only at extremely low incomes (well
  under 20% FPL). Treat as "low" confidence unless income is near zero.

Children's Medicaid (TX) — children under 19, by age of the child:
- Under age 1: income up to 198% FPL
- Ages 1-5:    income up to 144% FPL
- Ages 6-18:   income up to 133% FPL
- Free. Apply at YourTexasBenefits.com.

CHIP (TX) — children under 19 whose family income is too high for
Children's Medicaid but at or below 201% FPL. Low annual enrollment fee
(up to $50 per family) and small copays. Apply at YourTexasBenefits.com.
URL: https://www.yourtexasbenefits.com

Medicaid for Pregnant Women (TX) — pregnant, income up to 198% FPL. Covers
pregnancy and 12 months postpartum. Apply at YourTexasBenefits.com.

CHIP Perinatal (TX) — pregnant, income up to 202% FPL, and not eligible
for Medicaid (including because of immigration status). Covers prenatal
care and delivery for the unborn child.

Emergency Medicaid (TX) — people who would meet Medicaid rules except for
immigration status. Covers emergency medical conditions only (including
labor and delivery).

ACA Marketplace premium tax credits — HealthCare.gov (Texas uses the
federal marketplace).
- Household income from 100% to 400% FPL.
- Must be a US citizen or lawfully present, not eligible for Medicaid/CHIP,
  and without an affordable employer plan.
- Below 100% FPL in Texas is the "coverage gap": too poor for subsidies and
  not eligible for adult Medicaid. Say this plainly when it applies and
  point to community health centers (findahealthcenter.hrsa.gov).
- Open enrollment runs Nov 1 - Jan 15; losing other coverage, having a
  baby, or moving opens a 60-day Special Enrollment Period.
URL: https://www.healthcare.gov

Medicare — age 65+, or under 65 after receiving SSDI for 24 months (or with
ALS/ESRD). Apply through Social Security. URL: https://www.medicare.gov

Medicare Savings Programs and Extra Help (Part D Low Income Subsidy) — a
separate program from Medicare itself. Lowers premiums, deductibles, copays
and drug costs for Medicare enrollees with limited income and resources.
The quiz does not ask about resources, so this is "medium" confidence at best.
URL: https://www.medicare.gov

Medicaid for the Elderly and People with Disabilities (TX) — age 65+ or
with a disability, SSI-level income and limited resources ($2,000 individual
/ $3,000 couple). People receiving SSI get Medicaid automatically.
The quiz does not ask about resources, so unless the person receives SSI,
eligibility is "medium" confidence at best.
"""
