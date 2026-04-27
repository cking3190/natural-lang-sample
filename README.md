# ESG Natural Language Assistant (MongoDB + Guardrails)

This project is a Streamlit-based ESG assistant that converts natural language questions into MongoDB queries, validates them through strict guardrails, executes them safely, and returns readable answers with traceable pipeline steps.

## What Was Built

The system is built as a deterministic LangGraph workflow in [`agent/agent.py`](/Users/chris.king/c/ESGDemo/agent/agent.py):

1. `Schema Enrichment`
2. `MQL Generation`
3. `Guardrails + Execution`
4. `Response Synthesis`

Supporting modules:

- [`data/data_generator.py`](/Users/chris.king/c/ESGDemo/data/data_generator.py): seeds realistic synthetic ESG data and indexes.
- [`data/schema_registry.py`](/Users/chris.king/c/ESGDemo/data/schema_registry.py): builds `esg_schema_registry` metadata used by the LLM and guardrails.
- [`agent/prompts.py`](/Users/chris.king/c/ESGDemo/agent/prompts.py): system prompt + few-shot examples.
- [`agent/tools.py`](/Users/chris.king/c/ESGDemo/agent/tools.py): schema context formatting, LLM response parsing, query execution wrapper.
- [`agent/guardrails.py`](/Users/chris.king/c/ESGDemo/agent/guardrails.py): field allowlist, index coverage checks, safety injection, audit logging.

## Architecture Idea

Core design principle: the LLM is only responsible for query intent translation, not for direct database access.  
Database safety and performance guarantees are enforced outside the model by code-level guardrails.

This separation gives:

- Better reliability: prompt drift does not bypass execution controls.
- Better security: queryable surface area is explicit (`queryable_fields`).
- Better performance protection: no-filter and non-indexed filters are rejected.
- Better observability: all attempts are logged into an audit collection.

## Build Flow (How This Was Built)

### 1) Data Foundation

`data/data_generator.py` generates 3 collections (`esg_emissions`, `esg_governance`, `esg_social`) across 50 companies and 10 reporting years (2014-2023), then creates indexes such as:

- `(company.ticker, reporting_year)` compound
- `company.sector`
- `reporting_year`
- metric-specific fields (for example `emissions.scope_1.value`, `esg_score.score`)

This indexing strategy is essential because guardrails later enforce index-backed filters.

### 2) Schema Enrichment (Idea + Implementation)

The schema enrichment idea is to package operational metadata into a dedicated collection (`esg_schema_registry`) and inject it into prompting.

Each registry entry contains:

- business description
- `queryable_fields` (allowlist source)
- `field_descriptions`
- `enum_values`
- `indexes` (for index-aware generation/execution)
- `common_query_patterns`
- sample documents

At runtime, `get_schema_context()` in [`agent/tools.py`](/Users/chris.king/c/ESGDemo/agent/tools.py) converts these docs into a structured text block and injects it into the system prompt.

Why this matters:

- The model sees only sanctioned fields and realistic shapes.
- Few-shot examples become grounded by live schema/index metadata.
- Guardrails and prompt constraints use the same registry source of truth.

### 3) MQL Generation (Idea + Implementation)

MQL generation uses a strict JSON contract in [`agent/prompts.py`](/Users/chris.king/c/ESGDemo/agent/prompts.py):

- output must include collection + query type + filter/pipeline + explanation
- rules enforce no `$regex`, mandatory filtering, sort/limit behavior for top-N/trends
- few-shot pairs cover trend, ranking, comparison, controversy, and aggregation patterns

Runtime behavior in `generate_mql`:

- build messages = system prompt + few-shot examples + user question
- call LLM with `temperature=0`
- parse response using `parse_llm_response`
- if JSON cannot be parsed, treat it as non-query/off-topic flow

### 4) Guardrails + Execution (Idea + Implementation)

This is the safety core in [`agent/guardrails.py`](/Users/chris.king/c/ESGDemo/agent/guardrails.py):

1. Field allowlist check: reject any field not in registry `queryable_fields`.
2. Index coverage check: reject filter fields not covered by at least one index (prefix-aware logic).
3. Safety injection:
   - enforce `maxTimeMS` (`MAX_QUERY_TIME_MS`)
   - inject `$limit` for pipelines if missing (`MAX_RESULT_LIMIT`)
   - apply default find limit when missing
4. Audit logging: write query, status, timing, and errors to `esg_query_audit`.

Only after passing validations does execution occur.

### 5) Response Synthesis (Idea + Implementation)

The current response synthesis is deterministic (non-LLM):

- prepends the LLM’s MQL explanation
- formats results as markdown tables
- handles no-results and guardrail-blocked paths with clear user feedback

This keeps the final answer predictable and avoids post-query hallucination.

## Prompting Guidelines By Phase

### A) Schema Enrichment Prompting Guidelines

Goal: maximize structured context quality before generation.

- Include full `queryable_fields` and field descriptions in the system prompt.
- Include enum lists for categorical disambiguation (sector, rating, severity).
- Include index definitions so model can prefer index-backed filters.
- Include concise sample docs to anchor nested field paths.
- Keep context formatted with stable headings (`Collection`, `Queryable Fields`, `Indexes`), as implemented in `get_schema_context()`.

Recommended instruction pattern:

```text
Use only fields in Queryable Fields. Prefer indexed filters. Match enum values exactly when applicable.
```

### B) MQL Generation Prompting Guidelines

Goal: force structured output and operationally safe query shapes.

- Require JSON-only output with explicit keys.
- Encode hard rules in the system prompt (no `$regex`, always filtered queries).
- Use few-shot examples for each recurring pattern:
  - trend/time series
  - top-N ranking
  - multi-company comparison (`$in`)
  - grouped averages (`$group`)
- Keep temperature low (`0`) to reduce structural variance.
- Include a short `explanation` field in output for user-facing synthesis.

Recommended instruction pattern:

```text
Return valid JSON only. Choose `aggregate` for group/rank/trend analysis; use `find` for direct lookups.
```

### C) Guardrails + Execution Prompting Guidelines

Goal: make model outputs naturally pass guardrails without relaxing guardrails.

- Instruct model to always provide selective filters (never broad scans).
- Prefer index-aligned fields in examples (ticker/year/sector).
- For top-N, explicitly require sort + limit.
- For comparisons, require `$in` over ticker.
- Avoid unsupported patterns (`$regex`, unknown fields).

Recommended instruction pattern:

```text
Use index-friendly filter fields and include filtering in every query.
```

### D) Response Synthesis Prompting Guidelines

Current implementation is rule-based; no synthesis prompt is used.  
If you later move to LLM-based synthesis, keep these constraints:

- summarize only from returned rows (no extrapolation)
- preserve metric names/units exactly
- include count + execution timing
- clearly indicate truncation when results exceed display window

Recommended instruction pattern:

```text
Summarize only the provided query results; do not infer facts not present in the data.
```

## Guardrail Best Practices

1. Use a schema registry as a single source of truth for both prompting and validation.
2. Enforce allowlist checks before any DB execution.
3. Enforce index coverage for filter fields; reject likely COLLSCAN queries.
4. Treat empty filters as invalid by default (except intentional computed-only aggregations, as handled here).
5. Inject runtime safety (`maxTimeMS`, limit) rather than trusting model compliance.
6. Log every attempt (pass/reject/error) with timing and query payload for auditability.
7. Return structured, user-readable rejection reasons (include which guardrail fired).
8. Keep guardrails model-agnostic and deterministic.
9. Unit-test both pass and fail paths for each guardrail layer (see [`tests/test_guardrails.py`](/Users/chris.king/c/ESGDemo/tests/test_guardrails.py)).
10. Keep limits configurable (`MAX_QUERY_TIME_MS`, `MAX_RESULT_LIMIT`) and aligned with guardrail assumptions.

## Runbook

1. Create env and install:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Configure env:

```bash
cp .env.example .env
# set OPENAI_API_KEY and MongoDB settings
```

3. Seed data + schema registry:

```bash
python data/data_generator.py
python data/schema_registry.py
```

4. Run tests:

```bash
python -m unittest discover -s tests
```

5. Start app:

```bash
streamlit run app.py
```

## Extension Notes

- To add a new ESG factor, update synthetic data + schema registry first, then add prompt examples, then add guardrail tests.
- To swap models, change `OPENAI_MODEL`/`OPENAI_BASE_URL` in [`config.py`](/Users/chris.king/c/ESGDemo/config.py); guardrail behavior remains unchanged.
