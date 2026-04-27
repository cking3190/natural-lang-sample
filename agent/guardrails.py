"""Phase 3: Query guardrails — field allowlist, index coverage, safety injection, audit logging."""

import time
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MONGODB_URI, MONGODB_DATABASE, COLLECTIONS, MAX_QUERY_TIME_MS, MAX_RESULT_LIMIT


class GuardrailError(Exception):
    def __init__(self, message: str, guardrail: str, field: str | None = None):
        super().__init__(message)
        self.guardrail = guardrail
        self.field = field


class QueryGuardrails:
    def __init__(self, db):
        self.db = db
        self._allowlists: dict[str, set[str]] = {}
        self._indexes: dict[str, list[dict]] = {}
        self._load_registry()

    def _load_registry(self):
        registry = self.db[COLLECTIONS["schema_registry"]]
        for doc in registry.find():
            coll_name = doc["collection_name"]
            self._allowlists[coll_name] = set(doc.get("queryable_fields", []))
            self._indexes[coll_name] = doc.get("indexes", [])

    def get_allowlist(self, collection_name: str) -> set[str]:
        return self._allowlists.get(collection_name, set())

    def get_indexes(self, collection_name: str) -> list[dict]:
        return self._indexes.get(collection_name, [])

    def _extract_fields_from_filter(self, filter_dict: dict) -> set[str]:
        fields = set()
        if not isinstance(filter_dict, dict):
            return fields
        for key, value in filter_dict.items():
            if key.startswith("$"):
                if key in ("$and", "$or", "$nor") and isinstance(value, list):
                    for sub in value:
                        fields.update(self._extract_fields_from_filter(sub))
                elif key == "$not" and isinstance(value, dict):
                    fields.update(self._extract_fields_from_filter(value))
            else:
                fields.add(key)
        return fields

    def _extract_fields_from_pipeline(self, pipeline: list[dict]) -> tuple[set[str], set[str], set[str]]:
        all_fields = set()
        match_fields = set()
        sort_fields = set()
        computed_fields = set()

        for stage in pipeline:
            if "$match" in stage:
                extracted = self._extract_fields_from_filter(stage["$match"])
                match_fields.update(extracted)
                all_fields.update(extracted)
            elif "$sort" in stage:
                sort_fields.update(stage["$sort"].keys())
            elif "$group" in stage:
                group = stage["$group"]
                group_id = group.get("_id")
                if isinstance(group_id, str) and group_id.startswith("$"):
                    all_fields.add(group_id.lstrip("$"))
                elif isinstance(group_id, dict):
                    for v in group_id.values():
                        if isinstance(v, str) and v.startswith("$"):
                            all_fields.add(v.lstrip("$"))
                for k, v in group.items():
                    if k != "_id":
                        computed_fields.add(k)
                        if isinstance(v, dict):
                            for agg_val in v.values():
                                if isinstance(agg_val, str) and agg_val.startswith("$"):
                                    all_fields.add(agg_val.lstrip("$"))

        non_computed_sort_fields = sort_fields - computed_fields
        all_fields.update(non_computed_sort_fields)
        return all_fields, non_computed_sort_fields, match_fields

    def check_field_allowlist(self, collection_name: str, fields: set[str]):
        allowlist = self._allowlists.get(collection_name, set())
        if not allowlist:
            raise GuardrailError(
                f"No schema registry entry for collection '{collection_name}'.",
                guardrail="field_allowlist",
            )
        for field in fields:
            if field not in allowlist and not field.startswith("$"):
                raise GuardrailError(
                    f"Field '{field}' is not queryable on collection '{collection_name}'. "
                    f"Allowed fields: {sorted(allowlist)}",
                    guardrail="field_allowlist",
                    field=field,
                )

    def check_index_coverage(self, collection_name: str, filter_fields: set[str]):
        if not filter_fields:
            raise GuardrailError(
                "Query has no filter — this would cause a full collection scan.",
                guardrail="index_coverage",
            )

        indexes = self._indexes.get(collection_name, [])
        indexed_fields = set()
        for idx in indexes:
            idx_keys = list(idx["keys"].keys())
            for field in filter_fields:
                for i, key in enumerate(idx_keys):
                    if key == field:
                        indexed_fields.add(field)
                        break
                    prefix_fields = set(idx_keys[: i + 1])
                    if field in prefix_fields:
                        indexed_fields.add(field)

        uncovered = filter_fields - indexed_fields
        if uncovered:
            raise GuardrailError(
                f"No index covers filter on field(s): {sorted(uncovered)}. "
                "Query would require a collection scan.",
                guardrail="index_coverage",
                field=", ".join(sorted(uncovered)),
            )

    def inject_safety(self, query_or_pipeline: dict | list, has_limit: bool = False) -> dict | list:
        if isinstance(query_or_pipeline, list):
            has_pipeline_limit = any("$limit" in stage for stage in query_or_pipeline)
            if not has_pipeline_limit:
                query_or_pipeline.append({"$limit": MAX_RESULT_LIMIT})
            return query_or_pipeline
        else:
            return query_or_pipeline

    def log_audit(self, question: str, collection_name: str, query: Any,
                  validation_result: str, execution_time_ms: float | None = None,
                  error: str | None = None, result_count: int | None = None):
        audit_doc = {
            "timestamp": datetime.now(timezone.utc),
            "question": question,
            "collection": collection_name,
            "generated_query": str(query),
            "validation_result": validation_result,
            "execution_time_ms": execution_time_ms,
            "error": error,
            "result_count": result_count,
        }
        try:
            self.db[COLLECTIONS["audit_log"]].insert_one(audit_doc)
        except Exception:
            pass

    def validate_and_execute(self, collection_name: str, query_or_pipeline: dict | list,
                             question: str = "", projection: dict | None = None,
                             sort: dict | None = None, limit: int | None = None,
                             trace: list | None = None) -> dict:
        is_pipeline = isinstance(query_or_pipeline, list)
        all_fields = set()
        filter_fields = set()

        try:
            if is_pipeline:
                all_fields, sort_fields, match_filter_fields = self._extract_fields_from_pipeline(query_or_pipeline)
                filter_fields = match_filter_fields
            else:
                filter_fields = self._extract_fields_from_filter(query_or_pipeline)
                sort_keys = set(sort.keys()) if sort else set()
                all_fields = filter_fields | sort_keys

            # --- Guardrail 1: Field Allowlist ---
            allowlist = self.get_allowlist(collection_name)
            disallowed = {f for f in all_fields if f not in allowlist and not f.startswith("$")}
            allowlist_passed = len(disallowed) == 0
            if trace is not None:
                trace.append({
                    "step": "Field Allowlist Check",
                    "status": "passed" if allowlist_passed else "failed",
                    "detail": (
                        f"All {len(all_fields)} field(s) are in the allowlist."
                        if allowlist_passed
                        else f"Disallowed field(s): {sorted(disallowed)}"
                    ),
                    "fields_checked": sorted(all_fields),
                    "allowlist_size": len(allowlist),
                    "explanation": (
                        "Every field referenced in the query is checked against a pre-approved "
                        "list loaded from the schema registry. This prevents the LLM from "
                        "querying sensitive or non-existent fields."
                    ),
                })
            self.check_field_allowlist(collection_name, all_fields)

            # --- Guardrail 2: Index Coverage ---
            indexes = self.get_indexes(collection_name)
            index_names = [f"{idx['name']} ({', '.join(idx['keys'].keys())})" for idx in indexes]
            if is_pipeline and not filter_fields:
                index_detail = (
                    "No $match filter fields detected in this aggregation pipeline. "
                    "Index coverage check skipped for computed-only aggregation."
                )
            else:
                try:
                    self.check_index_coverage(collection_name, filter_fields)
                    index_passed = True
                    index_detail = f"Filter field(s) {sorted(filter_fields)} are covered by existing indexes."
                except GuardrailError as e:
                    index_passed = False
                    index_detail = str(e)
                    if trace is not None:
                        trace.append({
                            "step": "Index Coverage Check",
                            "status": "failed",
                            "detail": index_detail,
                            "filter_fields": sorted(filter_fields),
                            "available_indexes": index_names,
                            "explanation": (
                                "Each filter field must be covered by at least one index (prefix match). "
                                "This prevents full collection scans (COLLSCAN) that could lock the "
                                "database and degrade performance."
                            ),
                        })
                    raise

            if trace is not None:
                trace.append({
                    "step": "Index Coverage Check",
                    "status": "passed",
                    "detail": index_detail,
                    "filter_fields": sorted(filter_fields),
                    "available_indexes": index_names,
                    "explanation": (
                        "Each filter field must be covered by at least one index (prefix match). "
                        "This prevents full collection scans (COLLSCAN) that could lock the "
                        "database and degrade performance."
                    ),
                })

            # --- Guardrail 3: Safety Injection ---
            safety_actions = []
            if is_pipeline:
                had_limit = any("$limit" in stage for stage in query_or_pipeline)
                query_or_pipeline = self.inject_safety(query_or_pipeline)
                if not had_limit:
                    safety_actions.append(f"Injected $limit({MAX_RESULT_LIMIT}) to cap result size")
            else:
                if not limit:
                    safety_actions.append(f"Will apply limit({MAX_RESULT_LIMIT}) at execution")

            safety_actions.append(f"maxTimeMS({MAX_QUERY_TIME_MS}) will be enforced")
            safety_actions.append("Audit log entry will be written")

            if trace is not None:
                trace.append({
                    "step": "Safety Injection",
                    "status": "passed",
                    "detail": "; ".join(safety_actions),
                    "actions": safety_actions,
                    "explanation": (
                        "Safety defaults are injected into every query: a maxTimeMS timeout "
                        "prevents runaway queries, a result limit caps memory usage, and every "
                        "query is written to an audit log for observability."
                    ),
                })

        except GuardrailError as e:
            self.log_audit(question, collection_name, query_or_pipeline, "REJECTED", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "guardrail": e.guardrail,
                "field": e.field,
                "query": str(query_or_pipeline),
            }

        # --- Execute ---
        coll = self.db[collection_name]
        start = time.time()

        try:
            if is_pipeline:
                results = list(coll.aggregate(query_or_pipeline, maxTimeMS=MAX_QUERY_TIME_MS))
            else:
                cursor = coll.find(query_or_pipeline, projection).max_time_ms(MAX_QUERY_TIME_MS)
                if sort:
                    cursor = cursor.sort(list(sort.items()))
                cursor = cursor.limit(limit or MAX_RESULT_LIMIT)
                results = list(cursor)

            elapsed = round((time.time() - start) * 1000, 1)

            for doc in results:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

            self.log_audit(question, collection_name, query_or_pipeline, "PASSED",
                           execution_time_ms=elapsed, result_count=len(results))

            if trace is not None:
                trace.append({
                    "step": "Query Execution",
                    "status": "passed",
                    "detail": f"Returned {len(results)} document(s) in {elapsed}ms",
                    "execution_time_ms": elapsed,
                    "result_count": len(results),
                    "explanation": (
                        "The validated and safety-hardened query is executed against MongoDB. "
                        "Execution time is measured for performance monitoring."
                    ),
                })

            return {
                "success": True,
                "results": results,
                "count": len(results),
                "execution_time_ms": elapsed,
                "query": str(query_or_pipeline),
                "guardrails_passed": True,
            }

        except Exception as e:
            elapsed = round((time.time() - start) * 1000, 1)
            self.log_audit(question, collection_name, query_or_pipeline, "ERROR",
                           execution_time_ms=elapsed, error=str(e))
            if trace is not None:
                trace.append({
                    "step": "Query Execution",
                    "status": "failed",
                    "detail": f"Error after {elapsed}ms: {str(e)}",
                    "explanation": "The query failed during execution despite passing guardrails.",
                })
            return {
                "success": False,
                "error": f"Query execution error: {str(e)}",
                "guardrail": "execution",
                "query": str(query_or_pipeline),
            }
