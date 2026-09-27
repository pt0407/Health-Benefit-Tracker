# BenefitsFinder — Claude Code Build Plan
> Congressional App Challenge 2026 | Team of 4 | Advanced Full-Stack + ML

---

## 1. Project Overview

**App Name:** BenefitsFinder  
**Tagline:** *Find the benefits you're owed. In minutes.*  
**Platform:** Web app (React frontend + FastAPI backend)  
**Core problem:** Most Americans eligible for federal and state benefit programs never claim them — not because they don't need them, but because the system is too complex to navigate. BenefitsFinder asks 10 simple questions and surfaces every program the user qualifies for, with exact next steps to apply.

**Why it wins the Congressional App Challenge:**
- Zero diagnostic liability (no medical claims)
- Directly enforces what Congress already cares about: benefits access, economic relief
- No past winner has built anything in this space (confirmed via 2022–2025 winner research)
- Personal story angle: nearly every American leaves money on the table
- Technically impressive: multi-component AI system with RAG, an agent, a quiz engine, and a results dashboard

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│  Quiz UI → Loading State → Results Dashboard            │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API calls
┌──────────────────────▼──────────────────────────────────┐
│                  BACKEND (FastAPI)                       │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐   ┌─────────────┐ │
│  │  Quiz       │    │  Eligibility │   │  Insurance  │ │
│  │  Processor  │───▶│  Matcher     │──▶│  Agent      │ │
│  └─────────────┘    └──────┬───────┘   └──────┬──────┘ │
│                            │                   │        │
│                     ┌──────▼───────────────────▼──────┐ │
│                     │         RAG Engine               │ │
│                     │  (LangChain + ChromaDB)          │ │
│                     └──────────────┬──────────────────┘ │
│                                    │                     │
│                     ┌──────────────▼──────────────────┐ │
│                     │       Knowledge Base             │ │
│                     │  Federal Programs + TX Benefits  │ │
│                     └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              EXTERNAL APIs                               │
│  Anthropic API (Claude) │ Benefits.gov API │ TX HHSC    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Component Breakdown

### Component 1 — Knowledge Base

**What it is:** A structured, pre-indexed database of every major federal and Texas-specific benefit program, chunked and embedded for RAG retrieval.

**Data sources (all free and public):**
- `Benefits.gov API` — Official US government benefits database. REST API, no key required for basic access. Returns program names, eligibility criteria, and application URLs.
- `USA.gov benefits data` — Downloadable JSON of federal programs
- `Texas HHSC` — Texas Health and Human Services Commission programs (downloadable PDFs, parse with PyPDF2)
- `Medicaid.gov` — State-specific Medicaid eligibility rules
- `USDA SNAP` — Income thresholds by family size and state

**Programs to include (minimum viable set):**

| Program | Type | Key eligibility factor |
|---|---|---|
| SNAP | Federal | Income ≤ 130% FPL |
| Medicaid | Federal/State | Income + age + disability |
| CHIP | Federal/State | Children under 19, income threshold |
| WIC | Federal | Pregnant/postpartum/infant, income |
| LIHEAP | Federal | Energy costs, income |
| Medicare Low Income Subsidy | Federal | Age 65+ or disability |
| TANF | Federal/State | Families with children, income |
| Social Security Disability (SSDI) | Federal | Disability status |
| TX Medicaid for Elderly/Disabled | State | Age/disability, income |
| TX Children's Medicaid | State | Age, income |
| TX CHIP Perinatal | State | Pregnant, income |
| TX Emergency Medicaid | State | Immigration status + emergency |
| TX Workforce Commission Benefits | State | Employment status |

**Build steps:**
```bash
# 1. Scrape and download all source data
python scripts/scrape_benefits_data.py

# 2. Parse PDFs and JSONs into structured program objects
python scripts/parse_programs.py

# 3. Chunk each program into 300-word segments
python scripts/chunk_documents.py

# 4. Embed and store in ChromaDB vector database
python scripts/index_to_chromadb.py
```

**Program data schema:**
```json
{
  "program_id": "snap_federal",
  "name": "SNAP (Food Stamps)",
  "type": "federal",
  "category": "nutrition",
  "description": "Monthly food assistance...",
  "eligibility": {
    "income_limit_pct_fpl": 130,
    "citizenship_required": false,
    "age_min": null,
    "age_max": null,
    "requires_children": false,
    "requires_disability": false,
    "requires_pregnancy": false
  },
  "estimated_monthly_value_usd": 281,
  "application_url": "https://www.benefits.gov/benefit/361",
  "documents_needed": ["ID", "Proof of income", "Utility bills"],
  "processing_time_days": 30,
  "source": "USDA FNS",
  "last_updated": "2025-01-01"
}
```

---

### Component 2 — The Quiz

**What it is:** A conversational 10-question intake flow that collects the eligibility inputs needed to match users to programs. Friendly, non-bureaucratic, mobile-responsive.

**Questions (in order):**

```
Q1:  What state do you live in?
     → Dropdown (start with Texas, expand later)

Q2:  How many people live in your household?
     → Number input (1–10+)

Q3:  What is your approximate annual household income?
     → Range selector: <$15k / $15–30k / $30–50k / $50–75k / $75k+

Q4:  Are you currently employed?
     → Yes / No / Self-employed / Recently unemployed

Q5:  What is your age?
     → Number input

Q6:  Do you have children under 19 in your household?
     → Yes / No → if Yes: how many, and their ages

Q7:  Is anyone in your household pregnant?
     → Yes / No

Q8:  Does anyone in your household have a disability?
     → Yes / No → if Yes: receiving disability benefits already?

Q9:  What is your current health insurance situation?
     → Uninsured / Employer plan / Marketplace / Medicaid/Medicare / Other

Q10: Are you a US citizen or legal permanent resident?
     → Yes / No / Prefer not to say
```

**Quiz output schema (sent to backend):**
```json
{
  "state": "TX",
  "household_size": 4,
  "annual_income": 32000,
  "income_bracket": "15-30k",
  "employment_status": "employed",
  "age": 34,
  "has_children": true,
  "children_ages": [6, 8],
  "is_pregnant": false,
  "has_disability": false,
  "insurance_status": "uninsured",
  "citizenship": "citizen"
}
```

**Frontend implementation:**
- React with step-by-step wizard (one question per screen)
- Progress bar at top
- Back/Next navigation
- Input validation before proceeding
- Final "Submit" sends JSON to `/api/match` endpoint
- Loading animation while results generate (~3–5 seconds)

---

### Component 3 — Insurance Coverage Agent

**What it is:** A dedicated AI agent (separate from the main eligibility matcher) that handles the specific complexity of insurance-related benefit programs. Insurance eligibility has layered logic (Medicaid vs CHIP vs marketplace subsidies vs Medicare) that benefits from its own reasoning chain.

**Why it's a separate agent:**
Insurance eligibility is a decision tree, not a simple threshold check. A user who is uninsured, age 34, income $32k, with 2 kids could qualify for:
- Medicaid (if income ≤ 138% FPL in expanded states)
- CHIP for their children (if children's income threshold met)
- ACA marketplace subsidies (premium tax credits)
- TX Children's Medicaid specifically
All at the same time, with different application processes.

**Agent implementation:**
```python
# backend/agents/insurance_agent.py

from anthropic import Anthropic

client = Anthropic()

INSURANCE_SYSTEM_PROMPT = """
You are an expert benefits navigator specializing in health insurance 
coverage programs. Given a user's profile, determine which health 
coverage programs they qualify for.

You have access to these programs:
- Medicaid (federal + state expansion rules)
- CHIP (Children's Health Insurance Program)  
- ACA Marketplace subsidies (premium tax credits)
- Medicare (age 65+ or disability)
- Texas-specific Medicaid programs

Rules:
- Use ONLY the eligibility rules provided in the context below
- Express confidence levels for each recommendation
- If the user is near an income threshold, flag this explicitly
- NEVER make up program details — cite only what is in context
- Output structured JSON only

Context:
{insurance_program_context}
"""

def run_insurance_agent(user_profile: dict, rag_context: str) -> dict:
    """
    Runs the insurance coverage agent and returns structured 
    coverage recommendations.
    """
    prompt = f"""
    User profile:
    {json.dumps(user_profile, indent=2)}
    
    Based on this profile and the program context, return a JSON object:
    {{
      "qualifies_for": [
        {{
          "program": "program name",
          "confidence": "high|medium|low",
          "reason": "plain English explanation",
          "monthly_value_usd": 0,
          "application_url": "url",
          "next_step": "exactly what to do first"
        }}
      ],
      "near_threshold_warnings": ["any income cliff warnings"],
      "notes": "any special considerations"
    }}
    """
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=INSURANCE_SYSTEM_PROMPT.format(
            insurance_program_context=rag_context
        ),
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.content[0].text)
```

---

### Component 4 — RAG Engine

**What it is:** The retrieval layer that prevents hallucination. Every AI output is grounded in retrieved text from the knowledge base — the LLM explains and formats, it never invents eligibility rules.

**Stack:** LangChain + ChromaDB (local, no external DB needed for demo)

**Implementation:**
```python
# backend/rag/rag_engine.py

from langchain_community.vectorstores import Chroma
from langchain_anthropic import AnthropicEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

class BenefitsRAG:
    def __init__(self):
        self.vectorstore = Chroma(
            persist_directory="./chroma_db",
            embedding_function=AnthropicEmbeddings()
        )
    
    def retrieve_relevant_programs(
        self, 
        user_profile: dict, 
        k: int = 10
    ) -> list[str]:
        """
        Converts user profile into a query and retrieves the most
        relevant program chunks from the knowledge base.
        """
        # Build a natural language query from the profile
        query = self._profile_to_query(user_profile)
        
        # Retrieve top-k most relevant chunks
        docs = self.vectorstore.similarity_search(query, k=k)
        
        return [doc.page_content for doc in docs]
    
    def _profile_to_query(self, profile: dict) -> str:
        """Converts structured profile into a retrieval query."""
        parts = []
        if profile["income_bracket"]:
            parts.append(f"low income household {profile['income_bracket']}")
        if profile["has_children"]:
            parts.append("families with children benefits")
        if profile["is_pregnant"]:
            parts.append("pregnant women assistance programs")
        if profile["has_disability"]:
            parts.append("disability benefits assistance")
        if profile["insurance_status"] == "uninsured":
            parts.append("health insurance coverage uninsured")
        parts.append(f"{profile['state']} state benefits programs")
        
        return " ".join(parts)
    
    def index_programs(self, programs: list[dict]):
        """One-time indexing of all benefit programs."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=50
        )
        
        texts = []
        metadatas = []
        
        for program in programs:
            # Convert program to text for embedding
            text = self._program_to_text(program)
            chunks = splitter.split_text(text)
            
            for chunk in chunks:
                texts.append(chunk)
                metadatas.append({
                    "program_id": program["program_id"],
                    "program_name": program["name"],
                    "source": program["source"]
                })
        
        self.vectorstore.add_texts(texts, metadatas=metadatas)
        self.vectorstore.persist()
```

---

### Component 5 — Eligibility Matching Engine

**What it is:** The core business logic layer. Takes quiz outputs, retrieves relevant program chunks via RAG, runs deterministic rule checks for hard thresholds, then uses the LLM to handle edge cases and generate explanations.

**Two-pass approach:**
1. **Hard rules pass** (deterministic, no LLM): Check income thresholds, age requirements, citizenship requirements against known cutoffs. Fast and reliable.
2. **Soft rules pass** (LLM-grounded): Handle edge cases, near-threshold situations, and generate plain-language explanations with citations.

```python
# backend/matching/eligibility_matcher.py

FEDERAL_POVERTY_LEVELS_2025 = {
    1: 15650, 2: 21150, 3: 26650, 4: 32150,
    5: 37650, 6: 43150, 7: 48650, 8: 54150
}

class EligibilityMatcher:
    def __init__(self, rag_engine, insurance_agent):
        self.rag = rag_engine
        self.insurance_agent = insurance_agent
        self.client = Anthropic()
    
    def match(self, user_profile: dict) -> dict:
        # Pass 1: Hard rule checks
        hard_matches = self._hard_rule_check(user_profile)
        
        # Retrieve relevant RAG context
        rag_context = self.rag.retrieve_relevant_programs(user_profile)
        
        # Pass 2: LLM explanation + edge cases
        explained_matches = self._llm_explain(
            user_profile, hard_matches, rag_context
        )
        
        # Run insurance agent separately
        insurance_results = self.insurance_agent.run(
            user_profile, 
            "\n".join(rag_context)
        )
        
        # Combine and rank by estimated value
        all_matches = explained_matches + insurance_results["qualifies_for"]
        ranked = sorted(
            all_matches, 
            key=lambda x: x.get("monthly_value_usd", 0), 
            reverse=True
        )
        
        return {
            "matched_programs": ranked,
            "total_estimated_annual_value": sum(
                m.get("monthly_value_usd", 0) * 12 for m in ranked
            ),
            "warnings": insurance_results.get("near_threshold_warnings", [])
        }
    
    def _hard_rule_check(self, profile: dict) -> list:
        """Fast deterministic checks for clear eligibility."""
        matches = []
        fpl = FEDERAL_POVERTY_LEVELS_2025.get(profile["household_size"], 54150)
        income = profile["annual_income"]
        income_pct_fpl = (income / fpl) * 100
        
        # SNAP: income ≤ 130% FPL
        if income_pct_fpl <= 130:
            matches.append({
                "program": "SNAP",
                "rule_matched": "income_threshold",
                "confidence": "high"
            })
        
        # CHIP: children under 19, income ≤ 200% FPL (TX)
        if profile["has_children"] and income_pct_fpl <= 200:
            matches.append({
                "program": "CHIP",
                "rule_matched": "children_income_threshold",
                "confidence": "high"
            })
        
        # WIC: pregnant or children under 5, income ≤ 185% FPL
        has_young_children = any(
            age <= 5 for age in profile.get("children_ages", [])
        )
        if (profile["is_pregnant"] or has_young_children) \
                and income_pct_fpl <= 185:
            matches.append({
                "program": "WIC",
                "rule_matched": "pregnancy_or_young_children",
                "confidence": "high"
            })
        
        # LIHEAP: income ≤ 150% FPL
        if income_pct_fpl <= 150:
            matches.append({
                "program": "LIHEAP",
                "rule_matched": "income_threshold",
                "confidence": "high"
            })
            
        return matches
```

---

### Component 6 — Action Plan Generator

**What it is:** For each matched benefit, generates a specific, actionable next-steps plan. The gap between "you qualify" and "you applied" is where most people fall off — this component closes that gap.

**Output per program:**
```json
{
  "program": "SNAP",
  "monthly_value_usd": 281,
  "next_steps": [
    {
      "step": 1,
      "action": "Apply online at YourTexasBenefits.com",
      "url": "https://www.yourtexasbenefits.com",
      "time_required": "20–30 minutes"
    },
    {
      "step": 2,
      "action": "Gather these documents before you start",
      "documents": [
        "Photo ID (driver's license or passport)",
        "Proof of income (pay stubs, last 30 days)",
        "Proof of address (utility bill or lease)",
        "Social Security numbers for all household members"
      ]
    },
    {
      "step": 3,
      "action": "Attend your phone or in-person interview",
      "note": "You will be contacted within 7 days to schedule"
    }
  ],
  "processing_time": "Up to 30 days",
  "tip": "Apply even if you're unsure — the caseworker will verify eligibility"
}
```

---

### Component 7 — Results Dashboard

**What it is:** The visual output layer. Clean, scannable, emotionally impactful. The headline number ("You may be eligible for $6,200/year in benefits") is the demo moment.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  💰 You may qualify for up to                   │
│     $6,200/year in benefits                     │
│     across 4 programs                           │
└─────────────────────────────────────────────────┘

┌──────────────────────────────────┐
│  ✅ SNAP — Food Assistance       │
│  ~$281/month · High confidence   │
│  [Apply Now] [Learn More]        │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  ✅ CHIP — Children's Insurance  │
│  ~$0 premium · High confidence   │
│  [Apply Now] [Learn More]        │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  ✅ LIHEAP — Energy Assistance   │
│  ~$1,400/year · Medium confidence│
│  [Apply Now] [Learn More]        │
└──────────────────────────────────┘

⚠️  You're near the SNAP income cliff.
    If your income increases above $41,800,
    you may lose eligibility.
```

---

## 4. Full Tech Stack

### Frontend
```
React 18
React Router (multi-step quiz routing)
TailwindCSS (styling)
Recharts (value visualization on results page)
Axios (API calls)
```

### Backend
```
Python 3.11
FastAPI (REST API)
LangChain (RAG orchestration)
ChromaDB (local vector database)
Anthropic Python SDK (Claude claude-sonnet-4-6)
PyPDF2 (PDF parsing for TX HHSC documents)
Pydantic (data validation)
```

### Data & Indexing
```
Benefits.gov API (federal program data)
ChromaDB (vector store, persisted locally)
JSON flat files (program schemas, offline capable)
```

### Dev Tools
```
Uvicorn (FastAPI server)
Vite (React dev server)
pytest (backend testing)
```

---

## 5. File Structure

```
benefitsfinder/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Quiz/
│   │   │   │   ├── QuizWizard.jsx       # Main wizard container
│   │   │   │   ├── QuizStep.jsx         # Individual question step
│   │   │   │   ├── ProgressBar.jsx      # Progress indicator
│   │   │   │   └── questions.js         # Question definitions
│   │   │   ├── Results/
│   │   │   │   ├── ResultsDashboard.jsx # Main results page
│   │   │   │   ├── ProgramCard.jsx      # Individual benefit card
│   │   │   │   ├── HeroNumber.jsx       # "$6,200/year" headline
│   │   │   │   ├── ActionPlan.jsx       # Step-by-step apply modal
│   │   │   │   └── WarningBanner.jsx    # Threshold warnings
│   │   │   └── shared/
│   │   │       ├── LoadingSpinner.jsx
│   │   │       └── ErrorBoundary.jsx
│   │   ├── api/
│   │   │   └── benefitsApi.js           # API call wrappers
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── main.py                          # FastAPI app entry point
│   ├── routers/
│   │   └── benefits.py                  # /api/match endpoint
│   ├── matching/
│   │   └── eligibility_matcher.py       # Component 5
│   ├── agents/
│   │   └── insurance_agent.py           # Component 3
│   ├── rag/
│   │   └── rag_engine.py                # Component 4
│   ├── models/
│   │   ├── user_profile.py              # Pydantic schemas
│   │   └── program.py
│   └── requirements.txt
│
├── data/
│   ├── programs/
│   │   ├── federal_programs.json        # All federal programs
│   │   └── texas_programs.json          # TX-specific programs
│   ├── scripts/
│   │   ├── scrape_benefits_data.py      # Data collection
│   │   ├── parse_programs.py            # PDF/JSON parsing
│   │   └── index_to_chromadb.py         # One-time indexing
│   └── chroma_db/                       # Persisted vector DB
│
└── README.md
```

---

## 6. API Endpoints

```python
# POST /api/match
# Input: user quiz responses
# Output: matched programs + action plans

# GET /api/programs
# Returns: full list of programs in knowledge base

# GET /api/programs/{program_id}
# Returns: detailed info for one program

# POST /api/insurance-check
# Input: user profile
# Output: insurance coverage recommendations only
```

**Main endpoint contract:**
```python
# Request
POST /api/match
{
  "state": "TX",
  "household_size": 4,
  "annual_income": 32000,
  "employment_status": "employed",
  "age": 34,
  "has_children": true,
  "children_ages": [6, 8],
  "is_pregnant": false,
  "has_disability": false,
  "insurance_status": "uninsured",
  "citizenship": "citizen"
}

# Response
{
  "matched_programs": [...],
  "total_estimated_annual_value": 6200,
  "total_estimated_monthly_value": 517,
  "program_count": 4,
  "warnings": ["You are near the SNAP income threshold..."],
  "generated_at": "2026-09-27T14:32:00Z"
}
```

---

## 7. Team Split

| Member | Owns | Key files |
|---|---|---|
| Person 1 | Backend API + Eligibility Matcher | `main.py`, `eligibility_matcher.py`, `benefits.py` |
| Person 2 | RAG Engine + Knowledge Base indexing | `rag_engine.py`, `data/scripts/`, `chroma_db/` |
| Person 3 | Frontend Quiz + Results Dashboard | `QuizWizard.jsx`, `ResultsDashboard.jsx`, all components |
| Person 4 | Insurance Agent + Action Plan Generator + Demo video | `insurance_agent.py`, `ActionPlan.jsx`, pitch narrative |

---

## 8. Build Timeline

### Week 1–2: Foundation
- [ ] Set up project structure and repos
- [ ] Scrape and parse all program data (Person 2)
- [ ] Build ChromaDB index (Person 2)
- [ ] Build FastAPI skeleton with `/api/match` stub (Person 1)
- [ ] Build React quiz wizard UI (Person 3)

### Week 3–4: Core Logic
- [ ] Implement hard-rule eligibility matcher (Person 1)
- [ ] Implement RAG retrieval engine (Person 2)
- [ ] Wire quiz frontend to backend API (Person 3)
- [ ] Build insurance agent (Person 4)

### Week 5–6: Polish
- [ ] Build results dashboard with program cards (Person 3)
- [ ] Build action plan modal (Person 4)
- [ ] Add warning banners for threshold cases (Person 1)
- [ ] End-to-end testing with 10+ realistic profiles (all)

### Week 7: Demo Prep
- [ ] Deploy to Vercel (frontend) + Railway (backend)
- [ ] Film demo video — 3 minutes max
- [ ] Prepare 5 demo profiles covering different scenarios
- [ ] Write submission narrative (personal story + impact)

---

## 9. Demo Script (for submission video)

**Opening (15 sec):** "Billions of dollars in federal and state benefits go unclaimed every year — not because people don't need them, but because the system is impossible to navigate. We built BenefitsFinder to fix that."

**Demo flow (90 sec):**
1. Open the web app, start the quiz
2. Speed through 10 questions for a family of 4, income $32k, uninsured, 2 kids
3. Hit submit → watch loading animation with "Searching 47 programs..."
4. Results appear: **"You may qualify for $6,200/year across 4 programs"**
5. Click SNAP card → Action Plan expands with exact steps and documents needed
6. Click Insurance Coverage → insurance agent results appear, CHIP for children highlighted
7. Show warning banner: "You're near the income cliff for SNAP"

**Closing (15 sec):** "Every number you see traces back to official government data — the AI explains, it never invents. BenefitsFinder makes the system work for the people it was built to serve."

---

## 10. Key Technical Talking Points for Judges

1. **"How do you prevent hallucination?"** → RAG architecture: the LLM only explains retrieved government data, it never generates eligibility rules from scratch. Every output cites its source.

2. **"What makes this different from Benefits.gov?"** → Benefits.gov lists programs. BenefitsFinder matches you to them, ranks by value, and tells you exactly how to apply — in under 2 minutes.

3. **"Why a separate insurance agent?"** → Insurance eligibility has layered decision logic (Medicaid vs CHIP vs ACA subsidies) that benefits from isolated reasoning. Multi-agent architecture is more accurate and maintainable than a single monolithic prompt.

4. **"How do you keep the data current?"** → The knowledge base indexing script can be re-run to pull fresh data from Benefits.gov API and Texas HHSC. For the demo, data is current as of September 2026.

5. **"What's the impact?"** → 15 million Texans, 37 million Americans nationally are estimated to be eligible for SNAP but not enrolled. If BenefitsFinder helped 1% of them apply, that's $1B+ in benefits reaching people who need it.
