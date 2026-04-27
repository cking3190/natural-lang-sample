"""Phase 4: LangGraph structured workflow for ESG natural language queries."""

import json
import time
from typing import Annotated, TypedDict

from pymongo import MongoClient
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MONGODB_URI, MONGODB_DATABASE, OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL
from agent.guardrails import QueryGuardrails
from agent.prompts import SYSTEM_PROMPT, format_few_shot_messages
from agent.tools import get_schema_context, parse_llm_response, execute_parsed_query, NonESGQueryError


def _overwrite(a, b):
    return b if b is not None else a


def _merge_lists(a, b):
    if a is None:
        a = []
    if b is None:
        b = []
    return a + b


class GraphState(TypedDict, total=False):
    user_message: Annotated[str, _overwrite]
    schema_context: Annotated[str, _overwrite]
    generated_mql: Annotated[dict, _overwrite]
    query_result: Annotated[dict, _overwrite]
    response: Annotated[str, _overwrite]
    error: Annotated[str, _overwrite]
    trace: Annotated[list, _merge_lists]


class ESGQueryWorkflow:
    def __init__(self, mongo_uri=None, db_name=None, openai_api_key=None,
                 openai_model=None, openai_base_url=None):
        self.client = MongoClient(mongo_uri or MONGODB_URI)
        self.db = self.client[db_name or MONGODB_DATABASE]
        self.guardrails = QueryGuardrails(self.db)

        self.llm = ChatOpenAI(
            model=openai_model or OPENAI_MODEL,
            temperature=0,
            api_key=openai_api_key or OPENAI_API_KEY,
            base_url=openai_base_url or OPENAI_BASE_URL,
        )

        self._schema_context = get_schema_context(self.db)
        self.graph = self._build_graph()

    def _build_graph(self):
        def enrich_context(state: dict) -> dict:
            ctx = self._schema_context
            collections_loaded = []
            for line in ctx.split("\n"):
                if line.strip().startswith("### Collection:"):
                    collections_loaded.append(line.strip().replace("### Collection: ", ""))

            field_count = ctx.count("  - ")
            snippet = ctx[:600] + "..." if len(ctx) > 600 else ctx

            return {
                "schema_context": ctx,
                "trace": [{
                    "step": "Schema Enrichment",
                    "status": "passed",
                    "detail": (
                        f"Loaded schema context for {len(collections_loaded)} collection(s): "
                        f"{', '.join(collections_loaded)}. "
                        f"~{field_count} field descriptions, enum values, indexes, and sample docs "
                        "injected into the LLM prompt."
                    ),
                    "collections": collections_loaded,
                    "context_length_chars": len(ctx),
                    "context_preview": snippet,
                    "explanation": (
                        "The schema registry is fetched from MongoDB. It tells the LLM exactly "
                        "which collections exist, what fields are queryable, what indexes are "
                        "available, and provides sample documents so the LLM understands the "
                        "data shape. This is what makes the generated MQL accurate."
                    ),
                }],
            }

        def generate_mql(state: dict) -> dict:
            system_msg = SYSTEM_PROMPT.format(schema_context=state["schema_context"])
            few_shot = format_few_shot_messages()
            messages = [{"role": "system", "content": system_msg}]
            messages.extend(few_shot)
            messages.append({"role": "user", "content": state["user_message"]})

            prompt_trace = {
                "step": "LLM Prompt Construction",
                "status": "passed",
                "detail": (
                    f"Built prompt with {len(messages)} messages: 1 system prompt "
                    f"({len(system_msg):,} chars), {len(few_shot)} few-shot examples, "
                    f"1 user message."
                ),
                "system_prompt_preview": system_msg[:500] + "..." if len(system_msg) > 500 else system_msg,
                "few_shot_count": len(few_shot) // 2,
                "few_shot_questions": [m["content"] for m in few_shot if m["role"] == "user"],
                "user_message": state["user_message"],
                "total_prompt_chars": sum(len(m["content"]) for m in messages),
                "explanation": (
                    "The prompt is assembled from three parts: (1) a system prompt with strict "
                    "rules and the full schema context, (2) few-shot examples showing the LLM "
                    "correct input/output pairs for common ESG queries, and (3) the user's "
                    "natural language question. Few-shot examples dramatically improve MQL accuracy."
                ),
            }

            start = time.time()
            try:
                response = self.llm.invoke(messages)
                elapsed_ms = round((time.time() - start) * 1000, 1)
                raw_response = response.content
                parsed = parse_llm_response(raw_response)

                mql_trace = {
                    "step": "MQL Generation (LLM Call)",
                    "status": "passed",
                    "detail": (
                        f"LLM returned valid JSON in {elapsed_ms}ms. "
                        f"Query type: {parsed.get('query_type', 'unknown')}, "
                        f"Collection: {parsed.get('collection', 'unknown')}."
                    ),
                    "llm_response_time_ms": elapsed_ms,
                    "raw_llm_response": raw_response,
                    "parsed_mql": parsed,
                    "query_type": parsed.get("query_type", "unknown"),
                    "target_collection": parsed.get("collection", "unknown"),
                    "explanation": (
                        "The LLM translates the natural language question into a structured "
                        "JSON containing the target collection, query type (find vs aggregate), "
                        "and the actual MQL filter/pipeline. The response is parsed and validated "
                        "as JSON before proceeding to guardrails."
                    ),
                }
                return {
                    "generated_mql": parsed,
                    "error": "",
                    "trace": [prompt_trace, mql_trace],
                }
            except NonESGQueryError as e:
                elapsed_ms = round((time.time() - start) * 1000, 1)
                return {
                    "error": "",
                    "generated_mql": {},
                    "response": (
                        "This question doesn't appear to be related to the ESG data in this system. "
                        "I can help with **environmental** metrics (emissions, energy, carbon intensity), "
                        "**social** metrics (workforce diversity, health & safety), and "
                        "**governance** metrics (board composition, ESG scores, controversies).\n\n"
                        f"*The model responded:* {e.llm_message}"
                    ),
                    "trace": [prompt_trace, {
                        "step": "MQL Generation (LLM Call)",
                        "status": "blocked",
                        "detail": (
                            "The LLM did not produce a MongoDB query because the question "
                            "is outside the scope of the ESG dataset."
                        ),
                        "llm_response_time_ms": elapsed_ms,
                        "raw_llm_response": e.llm_message,
                        "explanation": (
                            "The LLM recognized this question cannot be answered from the "
                            "available ESG collections and returned a text explanation instead "
                            "of a JSON query. This is expected behavior for off-topic questions."
                        ),
                    }],
                }
            except json.JSONDecodeError as e:
                elapsed_ms = round((time.time() - start) * 1000, 1)
                return {
                    "error": f"Failed to parse LLM response as JSON: {e}",
                    "generated_mql": {},
                    "trace": [prompt_trace, {
                        "step": "MQL Generation (LLM Call)",
                        "status": "failed",
                        "detail": f"LLM response was not valid JSON after {elapsed_ms}ms: {e}",
                        "llm_response_time_ms": elapsed_ms,
                        "explanation": "The LLM returned text that could not be parsed as JSON.",
                    }],
                }
            except Exception as e:
                elapsed_ms = round((time.time() - start) * 1000, 1)
                return {
                    "error": f"LLM error: {e}",
                    "generated_mql": {},
                    "trace": [prompt_trace, {
                        "step": "MQL Generation (LLM Call)",
                        "status": "failed",
                        "detail": f"LLM call failed after {elapsed_ms}ms: {e}",
                        "llm_response_time_ms": elapsed_ms,
                        "explanation": "The LLM API call encountered an error.",
                    }],
                }

        def validate_execute(state: dict) -> dict:
            if state.get("error"):
                return {}
            mql = state.get("generated_mql", {})
            if not mql:
                if state.get("response"):
                    return {}
                return {"error": "No MQL generated."}

            guardrail_trace = []
            result = execute_parsed_query(
                self.guardrails, mql, question=state["user_message"], trace=guardrail_trace
            )
            return {"query_result": result, "trace": guardrail_trace}

        def synthesize_response(state: dict) -> dict:
            if state.get("response") and not state.get("query_result"):
                synth_trace = {
                    "step": "Response Synthesis",
                    "status": "passed",
                    "detail": "Response was already generated (question outside ESG scope).",
                    "explanation": (
                        "The question was not related to ESG data, so the pipeline "
                        "returned an explanation instead of executing a query."
                    ),
                }
                return {"trace": [synth_trace]}

            if state.get("error"):
                synth_trace = {
                    "step": "Response Synthesis",
                    "status": "failed",
                    "detail": f"Error: {state['error']}",
                    "explanation": "An error occurred earlier in the pipeline, so no data results are available.",
                }
                return {
                    "response": f"I encountered an error: {state['error']}",
                    "trace": [synth_trace],
                }

            result = state.get("query_result", {})
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                guardrail = result.get("guardrail", "unknown")
                synth_trace = {
                    "step": "Response Synthesis",
                    "status": "blocked",
                    "detail": f"Query blocked by '{guardrail}' guardrail. Generating rejection explanation.",
                    "explanation": (
                        "When a guardrail rejects a query, the response explains WHY it was "
                        "rejected and suggests how to rephrase the question. This teaches users "
                        "the boundaries of safe querying."
                    ),
                }
                return {
                    "response": (
                        f"Your query was blocked by the **{guardrail}** guardrail: {error_msg}\n\n"
                        "Try rephrasing your question to use indexed fields, or add a more specific filter."
                    ),
                    "trace": [synth_trace],
                }

            mql = state.get("generated_mql", {})
            explanation = mql.get("explanation", "")
            results = result.get("results", [])
            count = result.get("count", 0)
            exec_time = result.get("execution_time_ms", 0)

            response_parts = [explanation]
            if count == 0:
                response_parts.append("\nNo results found for this query.")
            elif count <= 20:
                response_parts.append(f"\n**{count} result(s)** returned in {exec_time}ms:\n")
                response_parts.append(_format_results_as_table(results))
            else:
                response_parts.append(f"\n**{count} result(s)** returned in {exec_time}ms. Showing first 20:\n")
                response_parts.append(_format_results_as_table(results[:20]))

            synth_trace = {
                "step": "Response Synthesis",
                "status": "passed",
                "detail": (
                    f"Formatted {count} result(s) into a readable response with "
                    f"{'a table' if count > 0 else 'a no-results message'}."
                ),
                "explanation": (
                    "Raw MongoDB documents are flattened and formatted into a human-readable "
                    "table. The LLM's explanation of what the query does is prepended as context."
                ),
            }
            return {"response": "\n".join(response_parts), "trace": [synth_trace]}

        def should_continue(state: dict) -> str:
            if state.get("error"):
                return "synthesize"
            if state.get("response") and not state.get("generated_mql"):
                return "synthesize"
            return "validate"

        builder = StateGraph(GraphState)
        builder.add_node("enrich", enrich_context)
        builder.add_node("generate", generate_mql)
        builder.add_node("validate", validate_execute)
        builder.add_node("synthesize", synthesize_response)

        builder.set_entry_point("enrich")
        builder.add_edge("enrich", "generate")
        builder.add_conditional_edges("generate", should_continue, {
            "validate": "validate",
            "synthesize": "synthesize",
        })
        builder.add_edge("validate", "synthesize")
        builder.add_edge("synthesize", END)

        return builder.compile()

    def run(self, user_message: str) -> dict:
        initial_state = {
            "user_message": user_message,
            "schema_context": "",
            "generated_mql": {},
            "query_result": {},
            "response": "",
            "error": "",
            "trace": [],
        }

        final_state = self.graph.invoke(initial_state)

        return {
            "response": final_state.get("response", ""),
            "generated_mql": final_state.get("generated_mql", {}),
            "query_result": final_state.get("query_result", {}),
            "error": final_state.get("error", ""),
            "trace": final_state.get("trace", []),
        }

    def stream(self, user_message: str):
        """Yield pipeline updates progressively as each graph node completes."""
        initial_state = {
            "user_message": user_message,
            "schema_context": "",
            "generated_mql": {},
            "query_result": {},
            "response": "",
            "error": "",
            "trace": [],
        }

        accumulated = dict(initial_state)

        for chunk in self.graph.stream(initial_state):
            for node_name, state_update in chunk.items():
                new_trace = state_update.get("trace") or []
                for key, value in state_update.items():
                    if key == "trace":
                        accumulated["trace"] = (accumulated.get("trace") or []) + (value or [])
                    elif value is not None:
                        accumulated[key] = value

                yield {
                    "node": node_name,
                    "new_trace_steps": new_trace,
                    "state": {
                        "response": accumulated.get("response", ""),
                        "generated_mql": accumulated.get("generated_mql", {}),
                        "query_result": accumulated.get("query_result", {}),
                        "error": accumulated.get("error", ""),
                        "trace": list(accumulated.get("trace", [])),
                    },
                }


def _format_results_as_table(results: list[dict]) -> str:
    if not results:
        return ""

    def flatten(d, parent_key="", sep="."):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten(v, new_key, sep).items())
            elif isinstance(v, list):
                items.append((new_key, ", ".join(str(x) for x in v)))
            else:
                items.append((new_key, v))
        return dict(items)

    flat_results = [flatten(r) for r in results]
    all_keys = []
    seen = set()
    for r in flat_results:
        for k in r:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    header = "| " + " | ".join(all_keys) + " |"
    separator = "| " + " | ".join("---" for _ in all_keys) + " |"
    rows = []
    for r in flat_results:
        row = "| " + " | ".join(str(r.get(k, "")) for k in all_keys) + " |"
        rows.append(row)

    return "\n".join([header, separator] + rows)
