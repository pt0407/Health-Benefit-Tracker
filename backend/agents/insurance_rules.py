"""Baseline health-coverage eligibility rules for Texas.

Kept in line with Person 2's sourced records in data/programs/*.json (per-field
sources in data/sources/*_sources.json, verified 2026-10-12/13). The agent gets
this text plus the records the RAG engine retrieves for the household. The ACA
Marketplace section has no Person 2 record yet and is not independently verified.
"""

# Income limits are percentages of the federal poverty level (FPL) for the
# household size, before the 5% income disregard used for MAGI Medicaid.
TX_INSURANCE_RULES = """\
TEXAS HEALTH COVERAGE RULES (sources: Texas HHSC, Medicaid.gov, HealthCare.gov, SSA, Medicare.gov)

Texas has NOT expanded Medicaid under the ACA.
- Adults aged 19-64 who are not pregnant, not disabled and not caring for
  a child generally cannot get Medicaid in Texas at any income.
- Parents and caretaker relatives: the Medicaid.gov Texas profile (table dated
  December 1, 2023) lists 12% FPL. Texas HHSC publishes this limit only in
  dollars, so treat it as "low" confidence unless income is near zero.
- Full Medicaid and CHIP require U.S. citizenship or a qualified non-citizen
  status. HealthCare.gov says a recent law change limits full Medicaid and CHIP
  to certain immigration statuses. Emergency Medicaid and CHIP Perinatal are
  the exceptions below.

Children's Medicaid (TX) — children 18 or younger (some children with
disabilities aged 19 or 20 also qualify), by the age of the child:
- Under age 1: income up to 198% FPL
- Ages 1-5:    income up to 144% FPL
- Ages 6-18:   income up to 133% FPL
- Free. If family income is too high, HHSC automatically checks CHIP.
URL: https://www.yourtexasbenefits.com/Learn/Home

CHIP (TX) — children 18 or younger whose family income is above the
Children's Medicaid limit and at or below 201% FPL. A 90-day wait without
other insurance applies unless a good-cause exemption is met. Enrollment fee
of $50 or less per year and small copays, depending on income.
URL: https://www.yourtexasbenefits.com/Learn/Home

Medicaid for Pregnant Women (TX) — pregnant, income at or below 198% FPL.
Covers pregnancy and up to 12 months after the baby is born, including labor
and delivery. No interview. HHSC must decide within 15 business days.
URL: https://www.yourtexasbenefits.com/Learn/Home

CHIP Perinatal (TX) — a pregnant woman with no other health insurance whose
household income is from 199% to 202% FPL, OR at or below 202% FPL if she
cannot get Medicaid because of her immigration status. Covers prenatal care
for the unborn child, labor and delivery, and two doctor visits after the
pregnancy ends. For women at or below 198% FPL, hospital labor and delivery
charges are paid through Emergency Medicaid instead. No 90-day wait, enrollment fee or
copays. She must apply before the baby is born. HHSC must decide within 15
business days.
URL: https://www.yourtexasbenefits.com/Learn/Home

Emergency Medicaid (TX) — people who would qualify for Medicaid except for
their immigration status (non-immigrants, undocumented people, and certain
permanent residents). Income limits follow the regular program: 198% FPL for
pregnant women and children under 1, 144% for ages 1-5, 133% for ages 6-18;
elderly or disabled adults must meet SSI rules other than citizenship. No
percent limit is published for parents and caretakers here. Covers only
services needed to stabilize an emergency medical condition (including labor
and delivery), certified by the treating practitioner.
URL: https://www.yourtexasbenefits.com/Learn/Home

Medicaid for the Elderly and People with Disabilities (MEPD, TX) — age 65+ or
meets the Social Security definition of disability, U.S. citizen or qualified
non-citizen. Income is tested in dollars (from January 1, 2026):
- Community programs: SSI-based limit of $994 a month for one person ($1,491
  for a couple).
- Nursing facility, waiver and attendant care programs: a higher special
  limit of $2,982 a month ($5,964 for a couple).
Resources must generally be $2,000 or less ($3,000 for a couple). People
receiving SSI get Medicaid automatically. The quiz does not ask about
resources, so unless the person receives SSI this is "medium" confidence at best.
URL: https://www.yourtexasbenefits.com/Learn/Home

ACA Marketplace premium tax credits — HealthCare.gov (Texas uses the
federal marketplace).
- Household income from 100% to 400% FPL.
- Must be a U.S. citizen or lawfully present, not eligible for Medicaid/CHIP,
  and without an affordable employer plan.
- Below 100% FPL in Texas is the "coverage gap": too poor for subsidies and
  not eligible for adult Medicaid. Say this plainly when it applies and
  point to community health centers (findahealthcenter.hrsa.gov).
- Open enrollment runs Nov 1 - Jan 15; losing other coverage, having a
  baby, or moving opens a 60-day Special Enrollment Period.
URL: https://www.healthcare.gov

Medicare — age 65+, or under 65 after receiving SSDI for 24 months (or with
ALS/ESRD). Apply through Social Security. URL: https://www.medicare.gov

Medicare Part D Extra Help (Low-Income Subsidy) — a separate program that
lowers Medicare drug plan premiums, deductibles and copays. Needs Medicare
Part A or B and income below 150% FPL. In 2026 Medicare states the limits as
$23,940 a year for an individual and $32,460 for a married couple, with
resource limits of $18,090 and $36,100. People with full Medicaid, a Medicare
Savings Program, or SSI get it automatically; others apply through Social
Security. The quiz does not ask about resources, so this is "medium"
confidence at best unless the person gets Medicaid or SSI.
URL: https://www.ssa.gov/medicare/part-d-extra-help
"""
