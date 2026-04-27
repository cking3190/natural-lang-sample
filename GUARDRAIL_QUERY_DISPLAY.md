# Guardrail Blocked Query Display

This document explains how the app shows a pretty-formatted query when guardrails reject a request.

## End-to-End Flow

1. User submits a question in the Streamlit UI (`app.py`).
2. `ESGQueryWorkflow` in `agent/agent.py` runs:
   - `generate_mql` calls the LLM and stores parsed output in `generated_mql`.
   - `validate_execute` runs guardrails via `execute_parsed_query(...)`.
3. If a guardrail rejects the query, `QueryGuardrails.validate_and_execute(...)` returns:
   - `success: False`
   - `guardrail: <guardrail_name>` (for example `field_allowlist` or `index_coverage`)
   - `error: <reason>`
4. `synthesize_response` builds a blocked response message for the user, while `generated_mql` remains available in final state.
5. Back in `app.py`, the UI checks for a blocked guardrail result and renders the attempted query as JSON.

## Rendering Condition (UI)

In `app.py`, after workflow execution:

- `query_result = final_result.get("query_result", {})`
- `generated_mql = final_result.get("generated_mql", {})`

The query preview is shown only when all are true:

- `not query_result.get("success")`
- `query_result.get("guardrail")` exists
- `query_result.get("guardrail") != "execution"`

`execution` failures are excluded because those are runtime/database errors after guardrails, not guardrail rejections.

## Query Preview Builder

`build_guardrail_query_preview(generated_mql)` creates display-safe JSON:

- Always includes:
  - `collection`
  - `query_type`
- For `aggregate` queries:
  - `pipeline`
- For `find` queries:
  - `filter`
  - optional `projection`, `sort`, `limit` (only if present)

This keeps output concise and aligned with the original generated structure.

## Where It Is Displayed

When blocked:

- Immediate assistant response renders:
  - `Generated query (blocked by guardrails):`
  - `st.code(json.dumps(..., indent=2), language="json")`

The same payload is persisted in chat history:

- Stored as `guardrail_query` in `st.session_state.messages`
- Re-rendered for prior assistant messages on every rerun

This ensures users can inspect the rejected query even after additional interactions.

## Why This Works Reliably

- `generated_mql` is produced before validation, so it is available even when validation fails.
- Guardrail failures are explicitly tagged (`guardrail` field), enabling deterministic UI behavior.
- Rendering uses JSON pretty-printing for readability and debugging.
