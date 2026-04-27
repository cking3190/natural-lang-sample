# ESG Natural Language Chatbot — POC Project Plan

## Overview

A Python-based proof-of-concept that demonstrates natural language querying over ESG (Environmental, Social, Governance) data stored in MongoDB. The POC includes synthetic data generation, a LangChain-powered Text-to-MQL agent, and production-grade query guardrails to prevent collection scans and enforce safe query execution.

**Target demo time**: ~30 minutes
**Build effort**: 3–5 days (SA-led, solo build)
**Stack**: Python 3.11+, MongoDB (on-prem or local), LangChain + LangGraph, Streamlit (UI)

---

## Architecture

```
┌─────────────────────────────────┐
│  Streamlit Chat UI              │
│  (conversational interface)     │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  LangGraph Structured Workflow  │
│  ┌──────┐ ┌────────┐ ┌───────┐ │
│  │Intent│→│MQL Gen │→│Respond│ │
│  │Parse │ │(Toolkit)│ │Synth  │ │
│  └──────┘ └────────┘ └───────┘ │
└──────┬───────────┬──────────────┘
       │           │
┌──────▼──────┐ ┌──▼──────────────┐
│Schema       │ │Query Guardrails │
│Registry     │ │• Index validator│
│(metadata    │ │• Field allowlist│
│collection)  │ │• maxTimeMS      │
└──────┬──────┘ │• Result limiter │
       │        └──┬──────────────┘
┌──────▼───────────▼──────────────┐
│  MongoDB (local or on-prem)     │
│  ┌──────────┐ ┌───────────────┐ │
│  │esg_      │ │esg_           │ │
│  │emissions │ │governance     │ │
│  ├──────────┤ ├───────────────┤ │
│  │esg_      │ │esg_           │ │
│  │social    │ │schema_registry│ │
│  └──────────┘ └───────────────┘ │
└─────────────────────────────────┘
```

---

## Phase 1: Synthetic ESG Data Generator

**Goal**: Populate MongoDB with realistic, nested ESG data that mirrors real-world investment management datasets.

### Collections & Schema Design

#### `esg_emissions` — Climate/Environmental Metrics
```json
{
  "_id": ObjectId,
  "company": {
    "name": "Apple Inc.",
    "ticker": "AAPL",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "region": "North America",
    "country": "US"
  },
  "reporting_year": 2023,
  "reporting_framework": "GHG Protocol",
  "emissions": {
    "scope_1": {
      "value": 52400,
      "unit": "tCO2e",
      "verified": true,
      "verifier": "Deloitte"
    },
    "scope_2": {
      "market_based": { "value": 0, "unit": "tCO2e" },
      "location_based": { "value": 109200, "unit": "tCO2e" }
    },
    "scope_3": {
      "total": { "value": 25120000, "unit": "tCO2e" },
      "categories": {
        "purchased_goods": 18500000,
        "transportation": 2300000,
        "use_of_sold_products": 3100000,
        "business_travel": 220000,
        "employee_commuting": 180000
      }
    },
    "total": 25172400,
    "carbon_intensity": {
      "value": 65.8,
      "unit": "tCO2e/M$ revenue",
      "revenue_base_usd": 383000000000
    }
  },
  "targets": {
    "net_zero_target_year": 2030,
    "sbti_aligned": true,
    "reduction_target_pct": 75,
    "baseline_year": 2015
  },
  "energy": {
    "total_consumption_mwh": 2450000,
    "renewable_pct": 100,
    "renewable_sources": ["solar", "wind", "biogas"]
  },
  "metadata": {
    "data_source": "CDP",
    "last_updated": "2024-03-15",
    "confidence_score": 0.92
  }
}
```

#### `esg_governance` — Board & Policy Metrics
```json
{
  "_id": ObjectId,
  "company": { "name": "...", "ticker": "...", "sector": "..." },
  "reporting_year": 2023,
  "board": {
    "total_members": 8,
    "independent_pct": 87.5,
    "gender_diversity_pct": 37.5,
    "avg_tenure_years": 5.2,
    "esg_committee": true,
    "separate_chair_ceo": true
  },
  "policies": {
    "anti_corruption": true,
    "whistleblower_protection": true,
    "human_rights_policy": true,
    "supply_chain_due_diligence": true,
    "political_contributions_disclosed": true
  },
  "controversies": {
    "count": 2,
    "severity": "moderate",
    "categories": ["labor_practices", "data_privacy"]
  },
  "esg_score": {
    "provider": "MSCI",
    "rating": "AAA",
    "score": 8.9,
    "percentile": 95
  }
}
```

#### `esg_social` — Workforce & Community Metrics
```json
{
  "_id": ObjectId,
  "company": { "name": "...", "ticker": "...", "sector": "..." },
  "reporting_year": 2023,
  "workforce": {
    "total_employees": 161000,
    "gender_pay_gap_pct": 3.2,
    "diversity": {
      "women_pct": 35.1,
      "underrepresented_minorities_pct": 28.4,
      "women_in_leadership_pct": 31.2
    },
    "turnover_rate_pct": 12.1,
    "training_hours_per_employee": 42
  },
  "health_safety": {
    "injury_rate": 0.8,
    "fatalities": 0,
    "lost_time_injury_freq": 0.3
  },
  "community": {
    "charitable_giving_usd": 250000000,
    "volunteer_hours": 1200000
  }
}
```

### Data Generator Specs

- **Companies**: 50 companies across 8 sectors (Technology, Energy, Finance, Healthcare, Consumer, Industrial, Materials, Utilities)
- **Time range**: 10 years (2014–2023), one document per company per year per collection
- **Total documents**: ~1,500 (50 companies × 10 years × 3 collections)
- **Realistic trends**: Emissions should generally decline over time for companies with SBTi targets; governance diversity should increase; scores should correlate with E/S/G performance
- **Enum values**: Defined in constants for sectors, industries, reporting frameworks, ESG rating scales, renewable energy sources, controversy categories
- **Indexes created automatically**: Compound indexes on `(company.ticker, reporting_year)`, single-field on `company.sector`, `reporting_year`, `emissions.scope_1.value`, `esg_score.rating`

### Deliverable
`data_generator.py` — Run once to seed the database. Idempotent (drops and recreates collections). Prints summary stats on completion.

---

## Phase 2: Schema Registry

**Goal**: Give the LLM agent rich context about the data model so it generates accurate MQL.

### Registry Collection: `esg_schema_registry`

One document per collection, storing everything the LLM needs:

```json
{
  "collection_name": "esg_emissions",
  "description": "Climate and environmental metrics including greenhouse gas emissions by scope, carbon intensity, energy consumption, and reduction targets. One document per company per reporting year.",
  "sample_documents": [ /* 2-3 representative docs */ ],
  "field_descriptions": {
    "company.name": "Full legal name of the company",
    "company.ticker": "Stock ticker symbol (e.g., AAPL, MSFT)",
    "emissions.scope_1.value": "Direct GHG emissions in tonnes CO2 equivalent",
    "emissions.scope_2.market_based.value": "Indirect emissions from purchased energy (market-based method)",
    "emissions.carbon_intensity.value": "Emissions per million dollars of revenue"
    // ... all queryable fields
  },
  "enum_values": {
    "company.sector": ["Technology", "Energy", "Finance", ...],
    "reporting_framework": ["GHG Protocol", "TCFD", "SASB", ...],
    "energy.renewable_sources": ["solar", "wind", "biogas", "hydro", "geothermal"],
    "esg_score.rating": ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
  },
  "indexes": [
    { "keys": {"company.ticker": 1, "reporting_year": 1}, "name": "ticker_year" },
    { "keys": {"company.sector": 1}, "name": "sector" },
    { "keys": {"reporting_year": 1}, "name": "year" },
    { "keys": {"emissions.scope_1.value": 1}, "name": "scope1_value" }
  ],
  "queryable_fields": [
    "company.name", "company.ticker", "company.sector", "company.industry",
    "company.region", "company.country", "reporting_year",
    "emissions.scope_1.value", "emissions.scope_2.market_based.value",
    "emissions.scope_2.location_based.value", "emissions.scope_3.total.value",
    "emissions.total", "emissions.carbon_intensity.value",
    "targets.net_zero_target_year", "targets.sbti_aligned",
    "energy.renewable_pct"
  ],
  "common_query_patterns": [
    "Trend over time: filter by ticker, sort by reporting_year, project emissions fields",
    "Sector comparison: group by sector, aggregate emissions metrics",
    "Top N emitters: sort by emissions.total descending, limit N",
    "Year-over-year change: use $setWindowFields or application-side calculation"
  ]
}
```

### Deliverable
`schema_registry.py` — Builds the registry from the generated data. Auto-extracts sample docs and index definitions from the live database.

---

## Phase 3: Query Guardrails Module

**Goal**: Prevent collection scans, enforce safe query execution, and provide clear error messages when a query is rejected.

### Guardrail Chain (executed in order)

```
Generated MQL
     │
     ▼
┌─ Field Allowlist Check ──────────────────────┐
│  Parse filter/sort/group fields from the     │
│  generated query. Reject if any field is not │
│  in the collection's queryable_fields list.  │
│  Error: "Field 'x' is not queryable."        │
└──────────────────┬───────────────────────────┘
                   │ PASS
                   ▼
┌─ Index Coverage Check ───────────────────────┐
│  For each filter field, verify it's part of  │
│  at least one index (prefix match). Reject   │
│  if query would require a COLLSCAN.          │
│  Error: "No index covers filter on 'x'."    │
└──────────────────┬───────────────────────────┘
                   │ PASS
                   ▼
┌─ Safety Injection ───────────────────────────┐
│  • Inject maxTimeMS(5000) on every query     │
│  • Inject $limit(1000) if no limit present   │
│  • Inject $project to strip _id if not needed│
│  • Log the query for audit                   │
└──────────────────┬───────────────────────────┘
                   │ PASS
                   ▼
            Execute Query
```

### Implementation Details

- **Field allowlist**: Loaded from schema registry at startup. Cached per collection.
- **Index coverage**: Loaded from `db.collection.getIndexes()` at startup. For compound indexes, validates the query uses a prefix of the index key pattern.
- **Query parsing**: The LangChain toolkit generates MQL as Python dicts. Parse the filter dict keys, the `$sort` keys, and any `$match` stage keys in an aggregation pipeline.
- **Bypass for `$group` + `$sort` on computed fields**: Allow `$sort` on fields created by `$group` (e.g., `totalEmissions`) since those don't need storage-level indexes.
- **Audit log**: Write every generated + executed query to an `esg_query_audit` collection with timestamp, original NL question, generated MQL, validation result, and execution time.

### Deliverable
`guardrails.py` — Importable module with a `validate_and_execute(collection, query_or_pipeline)` function. Returns results or a structured error explaining why the query was rejected.

---

## Phase 4: LangChain Agent Integration

**Goal**: Wire the LangChain MongoDB Agent Toolkit into a structured workflow with the schema registry and guardrails.

### Agent Design

Use LangGraph's structured workflow (not pure ReAct) for predictability:

```python
# Simplified flow
class ESGQueryWorkflow:

    def parse_intent(self, user_message: str) -> dict:
        """Extract: company/sector, metric type, time range, comparison type"""

    def enrich_context(self, intent: dict) -> str:
        """Pull relevant schema registry docs, sample docs, enum values"""

    def generate_mql(self, user_message: str, context: str) -> dict:
        """LLM call with schema-enriched prompt → MQL query or pipeline"""

    def validate_and_execute(self, collection: str, query: dict) -> dict:
        """Run through guardrails chain, execute if valid"""

    def synthesize_response(self, results: dict, user_message: str) -> str:
        """Format results as natural language + optional table/chart data"""
```

### Prompt Engineering

The system prompt should include:
- The schema registry context for relevant collections
- Explicit instructions to only use fields from the queryable_fields list
- Examples of correct MQL for common ESG query patterns
- Instructions to use aggregation pipelines for trends, comparisons, and rankings
- Constraint: never use `$regex` on unindexed fields

### LLM Configuration

```python
# Supports any LangChain-compatible model
# For demo: OpenAI or Anthropic API
# For on-prem: swap to internal endpoint
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    base_url="https://internal-llm-endpoint.bank.com/v1"  # on-prem swap
)
```

### Demo Query Set (pre-tested)

| # | Natural Language Query | Expected MQL Pattern |
|---|---|---|
| 1 | "How have Apple's emissions trended over 10 years?" | `find({ticker: AAPL}).sort({year: 1}).project({year, scope_1, scope_2, scope_3})` |
| 2 | "Which sector has the highest average carbon intensity?" | `aggregate([{$group: {_id: sector, avg: {$avg: carbon_intensity}]}, {$sort}, {$limit}])` |
| 3 | "Compare Microsoft and Google Scope 1 emissions in 2023" | `find({ticker: {$in: [MSFT, GOOGL]}, year: 2023}).project(...)` |
| 4 | "Top 5 companies by renewable energy percentage" | `find({year: 2023}).sort({renewable_pct: -1}).limit(5)` |
| 5 | "Which companies have SBTi-aligned targets?" | `find({sbti_aligned: true, year: 2023}).project({ticker, name, net_zero_target_year})` |
| 6 | "Show me the board diversity trend for tech companies" | Cross-collection: governance + filter by sector |
| 7 | "Which companies had controversies in 2023?" | Governance collection, `controversies.count > 0` |
| 8 | "Average ESG score by sector" | `aggregate([{$group: {_id: sector, avg_score: {$avg: esg_score.score}}}])` |

### Guardrail Demo Queries (expected rejections)

| # | Query That Should Be Blocked | Guardrail That Fires |
|---|---|---|
| 1 | "Find all companies mentioning 'green' in their reports" | Field allowlist (no full-text field indexed) |
| 2 | "Show me everything in the database" | No filter → COLLSCAN risk |
| 3 | A query filtering on `metadata.confidence_score` | Index coverage (not indexed) |

### Deliverable
`agent.py` — The orchestration module. Exposes a `run(user_message: str) -> AgentResponse` function.

---

## Phase 5: Streamlit Chat UI

**Goal**: Simple, demo-ready conversational interface.

### Features
- Chat-style message history (user messages + agent responses)
- Expandable "Query Inspector" panel showing:
  - Generated MQL (syntax-highlighted)
  - Guardrail validation result (pass/fail with reason)
  - Execution time (ms)
  - Documents scanned vs returned
- Results displayed as formatted tables (pandas DataFrames)
- Optional: matplotlib/plotly chart for trend queries
- Sidebar with example queries (clickable)
- Connection status indicator (MongoDB + LLM)

### Layout
```
┌─────────────────────────────────────────────┐
│  ESG Data Assistant              [Connected]│
├─────────┬───────────────────────────────────┤
│ Example │  💬 How have Apple's emissions    │
│ Queries │     trended over 10 years?        │
│         │                                   │
│ • Trend │  🤖 Here's Apple's emissions      │
│ • Top N │     trend from 2014-2023:         │
│ • Comp. │                                   │
│ • Score │  ┌────────────────────────┐       │
│         │  │ Year │ Scope1 │ Scope2 │       │
│         │  │ 2014 │ 82,100 │ 45,200 │       │
│         │  │ ...  │ ...    │ ...    │       │
│         │  └────────────────────────┘       │
│         │                                   │
│         │  ▸ Query Inspector                │
│         │    MQL: db.esg_emissions.find(...) │
│         │    Guardrails: ✅ All passed       │
│         │    Execution: 12ms                │
│         │                                   │
│         │  ┌─────────────────────────┐      │
│         │  │ Ask about ESG data...   │ Send │
│         │  └─────────────────────────┘      │
├─────────┴───────────────────────────────────┤
│  ⚙ Settings: LLM Model | Max Results | DB  │
└─────────────────────────────────────────────┘
```

### Deliverable
`app.py` — Run with `streamlit run app.py`. Single file, no build step.

---

## Project Structure

```
esg-chatbot-poc/
├── README.md                  # Setup instructions + demo guide
├── requirements.txt           # Python dependencies
├── .env.example               # Template for API keys + connection strings
├── config.py                  # Centralized config (DB, LLM, guardrail thresholds)
│
├── data/
│   ├── data_generator.py      # Phase 1: Synthetic ESG data seeder
│   ├── schema_registry.py     # Phase 2: Build schema registry
│   └── constants.py           # Enum values, sector lists, company universe
│
├── agent/
│   ├── agent.py               # Phase 4: LangGraph workflow orchestration
│   ├── guardrails.py          # Phase 3: Query validation chain
│   ├── prompts.py             # System prompts + few-shot examples
│   └── tools.py               # Custom tool wrappers around the toolkit
│
├── app.py                     # Phase 5: Streamlit chat UI
│
└── tests/
    ├── test_guardrails.py     # Unit tests for guardrail chain
    ├── test_data_generator.py # Validate data shape + index creation
    └── test_queries.py        # Integration tests for demo query set
```

---

## Dependencies

```
# requirements.txt
langchain>=0.3.0
langchain-mongodb>=0.6.0
langgraph>=0.2.0
langchain-openai>=0.2.0     # swap for langchain-anthropic if using Claude
pymongo>=4.8
streamlit>=1.38
pandas>=2.1
plotly>=5.18
python-dotenv>=1.0
```

---

## Build Sequence & Effort Estimates

| Day | Phase | Deliverable | Effort |
|-----|-------|-------------|--------|
| 1 | Phase 1: Data Generator | `data_generator.py` + `constants.py` with 50 companies × 10 years × 3 collections seeded, indexes created | 4 hrs |
| 1 | Phase 2: Schema Registry | `schema_registry.py` populating `esg_schema_registry` collection | 2 hrs |
| 2 | Phase 3: Guardrails | `guardrails.py` with field allowlist, index coverage, safety injection, audit logging | 4 hrs |
| 2 | Phase 3: Guardrail Tests | `test_guardrails.py` covering pass/fail cases | 2 hrs |
| 3 | Phase 4: Agent | `agent.py` + `prompts.py` + `tools.py` with structured workflow, schema-enriched prompts | 6 hrs |
| 4 | Phase 4: Agent Tuning | Iterate on prompt engineering, test all 8 demo queries + 3 rejection queries | 4 hrs |
| 4 | Phase 5: Streamlit UI | `app.py` with chat, query inspector, example sidebar | 4 hrs |
| 5 | Polish & Package | README, .env.example, end-to-end testing, demo rehearsal | 4 hrs |

**Total: ~30 hours across 5 working days**

---

## Demo Script (30 minutes)

1. **Setup Context** (3 min) — Show the problem: ESG data in MongoDB, analysts dumping to Excel, no query interface
2. **Data Walkthrough** (5 min) — Show Compass with the generated data, highlight nested emissions structure, cross-collection design
3. **Simple Query** (5 min) — "How have Apple's emissions trended?" → Show the chat, the table result, open the Query Inspector to show generated MQL
4. **Aggregation Query** (5 min) — "Which sector has the highest carbon intensity?" → Show grouping/sorting, explain how the agent chose an aggregation pipeline
5. **Cross-Collection** (3 min) — "Show me tech companies with AAA ESG ratings and declining emissions" → Demonstrate multi-collection orchestration
6. **Guardrails Demo** (5 min) — Try a bad query ("find everything"), show the rejection message, explain index validation. Then show the audit log.
7. **Architecture Discussion** (4 min) — Walk the diagram: where the LLM sits, what swapping to on-prem looks like, how cloud would extend this

---

## Key Talking Points for the Client

- **This is not Compass "Generate Query"** — it's a purpose-built agent with guardrails. End users never see MQL. Index safety is enforced, not hoped for.
- **LLM is swappable** — Demo uses OpenAI API, but the LangChain abstraction means swapping to an internal LLM is a config change, not a rewrite.
- **Schema registry = control** — The client's team controls exactly what's queryable. Adding a new ESG factor is a registry update, not a code change.
- **Cloud migration path is built in** — V2 adds Atlas Vector Search for semantic queries ("companies with similar ESG profiles"), auto-embedding, and the MCP server. The on-prem architecture is designed so that migration is additive, not a rewrite.
- **Guardrails are the differentiator** — This is what separates a demo from production. The index validation + field allowlist + audit logging pattern is exactly what SecArch teams want to see.
