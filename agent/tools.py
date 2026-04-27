"""Custom tool wrappers for the ESG query agent."""

import json
from typing import Any

from pymongo import MongoClient

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MONGODB_URI, MONGODB_DATABASE, COLLECTIONS
from agent.guardrails import QueryGuardrails


def get_schema_context(db) -> str:
    registry = db[COLLECTIONS["schema_registry"]]
    docs = list(registry.find())

    context_parts = []
    for doc in docs:
        part = f"\n### Collection: {doc['collection_name']}\n"
        part += f"Description: {doc['description']}\n\n"

        part += "Queryable Fields:\n"
        for field in doc.get("queryable_fields", []):
            desc = doc.get("field_descriptions", {}).get(field, "")
            part += f"  - {field}: {desc}\n"

        part += "\nEnum Values:\n"
        for field, values in doc.get("enum_values", {}).items():
            part += f"  - {field}: {values}\n"

        part += "\nIndexes:\n"
        for idx in doc.get("indexes", []):
            part += f"  - {idx['name']}: {idx['keys']}\n"

        part += "\nCommon Query Patterns:\n"
        for pattern in doc.get("common_query_patterns", []):
            part += f"  - {pattern}\n"

        if doc.get("sample_documents"):
            part += "\nSample Document (first):\n"
            sample = doc["sample_documents"][0]
            part += json.dumps(sample, indent=2, default=str)[:2000] + "\n"

        context_parts.append(part)

    return "\n".join(context_parts)


class NonESGQueryError(Exception):
    """Raised when the LLM response indicates the question is not related to ESG data."""
    def __init__(self, llm_message: str):
        self.llm_message = llm_message
        super().__init__(llm_message)


def parse_llm_response(response_text: str) -> dict:
    text = response_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        json_text = text[start:end]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    raise NonESGQueryError(
        response_text if len(response_text) < 500
        else response_text[:500]
    )


def execute_parsed_query(guardrails: QueryGuardrails, parsed: dict,
                         question: str = "", trace: list | None = None) -> dict:
    collection_name = parsed.get("collection", "")
    query_type = parsed.get("query_type", "find")
    explanation = parsed.get("explanation", "")

    if query_type == "aggregate":
        pipeline = parsed.get("pipeline", [])
        result = guardrails.validate_and_execute(
            collection_name, pipeline, question=question, trace=trace
        )
    else:
        filter_dict = parsed.get("filter", {})
        projection = parsed.get("projection")
        sort = parsed.get("sort")
        limit = parsed.get("limit")
        result = guardrails.validate_and_execute(
            collection_name, filter_dict, question=question,
            projection=projection, sort=sort, limit=limit, trace=trace
        )

    result["explanation"] = explanation
    result["query_type"] = query_type
    result["collection"] = collection_name
    return result
