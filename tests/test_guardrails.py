"""Unit tests for the guardrails module."""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.guardrails import QueryGuardrails, GuardrailError


def _make_mock_db():
    mock_db = MagicMock()
    registry_docs = [
        {
            "collection_name": "esg_emissions",
            "queryable_fields": [
                "company.name", "company.ticker", "company.sector",
                "reporting_year", "emissions.scope_1.value", "emissions.total",
                "energy.renewable_pct", "targets.sbti_aligned",
                "emissions.carbon_intensity.value",
            ],
            "indexes": [
                {"keys": {"company.ticker": 1, "reporting_year": 1}, "name": "ticker_year"},
                {"keys": {"company.sector": 1}, "name": "sector"},
                {"keys": {"reporting_year": 1}, "name": "year"},
                {"keys": {"emissions.scope_1.value": 1}, "name": "scope1_value"},
                {"keys": {"emissions.total": 1}, "name": "total_emissions"},
                {"keys": {"energy.renewable_pct": 1}, "name": "renewable_pct"},
                {"keys": {"targets.sbti_aligned": 1}, "name": "sbti_aligned"},
            ],
        },
        {
            "collection_name": "esg_governance",
            "queryable_fields": [
                "company.name", "company.ticker", "company.sector",
                "reporting_year", "esg_score.rating", "esg_score.score",
                "controversies.count", "board.gender_diversity_pct",
            ],
            "indexes": [
                {"keys": {"company.ticker": 1, "reporting_year": 1}, "name": "ticker_year"},
                {"keys": {"company.sector": 1}, "name": "sector"},
                {"keys": {"reporting_year": 1}, "name": "year"},
                {"keys": {"esg_score.rating": 1}, "name": "esg_rating"},
                {"keys": {"esg_score.score": 1}, "name": "esg_score"},
                {"keys": {"controversies.count": 1}, "name": "controversy_count"},
                {"keys": {"board.gender_diversity_pct": 1}, "name": "board_diversity"},
            ],
        },
    ]
    mock_db.__getitem__ = MagicMock(side_effect=lambda key: {
        "esg_schema_registry": MagicMock(find=MagicMock(return_value=registry_docs)),
        "esg_query_audit": MagicMock(),
    }.get(key, MagicMock()))
    return mock_db


class TestFieldAllowlist(unittest.TestCase):
    def setUp(self):
        self.guardrails = QueryGuardrails.__new__(QueryGuardrails)
        self.guardrails.db = _make_mock_db()
        self.guardrails._allowlists = {}
        self.guardrails._indexes = {}
        self.guardrails._load_registry()

    def test_valid_fields_pass(self):
        self.guardrails.check_field_allowlist(
            "esg_emissions", {"company.ticker", "reporting_year"}
        )

    def test_invalid_field_rejected(self):
        with self.assertRaises(GuardrailError) as ctx:
            self.guardrails.check_field_allowlist(
                "esg_emissions", {"metadata.confidence_score"}
            )
        self.assertEqual(ctx.exception.guardrail, "field_allowlist")
        self.assertIn("metadata.confidence_score", str(ctx.exception))

    def test_unknown_collection_rejected(self):
        with self.assertRaises(GuardrailError):
            self.guardrails.check_field_allowlist("unknown_collection", {"foo"})

    def test_operator_fields_ignored(self):
        self.guardrails.check_field_allowlist("esg_emissions", {"$gt", "company.ticker"})


class TestIndexCoverage(unittest.TestCase):
    def setUp(self):
        self.guardrails = QueryGuardrails.__new__(QueryGuardrails)
        self.guardrails.db = _make_mock_db()
        self.guardrails._allowlists = {}
        self.guardrails._indexes = {}
        self.guardrails._load_registry()

    def test_indexed_field_passes(self):
        self.guardrails.check_index_coverage("esg_emissions", {"company.ticker"})

    def test_unindexed_field_rejected(self):
        with self.assertRaises(GuardrailError) as ctx:
            self.guardrails.check_index_coverage("esg_emissions", {"company.name"})
        self.assertEqual(ctx.exception.guardrail, "index_coverage")

    def test_empty_filter_rejected(self):
        with self.assertRaises(GuardrailError) as ctx:
            self.guardrails.check_index_coverage("esg_emissions", set())
        self.assertIn("no filter", str(ctx.exception).lower())

    def test_compound_index_prefix_passes(self):
        self.guardrails.check_index_coverage("esg_emissions", {"company.ticker"})

    def test_multiple_indexed_fields_pass(self):
        self.guardrails.check_index_coverage(
            "esg_emissions", {"company.sector", "reporting_year"}
        )


class TestFieldExtraction(unittest.TestCase):
    def setUp(self):
        self.guardrails = QueryGuardrails.__new__(QueryGuardrails)
        self.guardrails.db = _make_mock_db()
        self.guardrails._allowlists = {}
        self.guardrails._indexes = {}
        self.guardrails._load_registry()

    def test_simple_filter(self):
        fields = self.guardrails._extract_fields_from_filter({"company.ticker": "AAPL"})
        self.assertEqual(fields, {"company.ticker"})

    def test_nested_and_or(self):
        fields = self.guardrails._extract_fields_from_filter({
            "$and": [
                {"company.ticker": "AAPL"},
                {"$or": [{"reporting_year": 2023}, {"emissions.total": {"$gt": 100}}]}
            ]
        })
        self.assertEqual(fields, {"company.ticker", "reporting_year", "emissions.total"})

    def test_pipeline_extraction(self):
        pipeline = [
            {"$match": {"reporting_year": 2023}},
            {"$group": {"_id": "$company.sector", "avg": {"$avg": "$emissions.total"}}},
            {"$sort": {"avg": -1}},
        ]
        all_fields, sort_fields, match_fields = self.guardrails._extract_fields_from_pipeline(pipeline)
        self.assertIn("reporting_year", all_fields)
        self.assertIn("company.sector", all_fields)
        self.assertIn("emissions.total", all_fields)
        self.assertEqual(match_fields, {"reporting_year"})
        self.assertEqual(sort_fields, set())

    def test_pipeline_without_match_skips_index_coverage(self):
        pipeline = [
            {"$group": {"_id": "$company.sector", "avg": {"$avg": "$emissions.carbon_intensity.value"}}},
            {"$sort": {"avg": -1}},
            {"$limit": 1},
        ]
        result = self.guardrails.validate_and_execute("esg_emissions", pipeline, question="test")
        self.assertTrue(result["success"])


class TestSafetyInjection(unittest.TestCase):
    def setUp(self):
        self.guardrails = QueryGuardrails.__new__(QueryGuardrails)
        self.guardrails.db = _make_mock_db()
        self.guardrails._allowlists = {}
        self.guardrails._indexes = {}
        self.guardrails._load_registry()

    def test_pipeline_gets_limit(self):
        pipeline = [{"$match": {"reporting_year": 2023}}]
        result = self.guardrails.inject_safety(pipeline)
        limits = [s for s in result if "$limit" in s]
        self.assertTrue(len(limits) > 0)

    def test_pipeline_existing_limit_preserved(self):
        pipeline = [{"$match": {"reporting_year": 2023}}, {"$limit": 5}]
        result = self.guardrails.inject_safety(pipeline)
        limits = [s for s in result if "$limit" in s]
        self.assertEqual(len(limits), 1)
        self.assertEqual(limits[0]["$limit"], 5)


if __name__ == "__main__":
    unittest.main()
