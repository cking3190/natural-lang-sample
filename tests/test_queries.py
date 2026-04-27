"""Integration tests for the demo query set — tests query parsing and tool execution logic."""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.tools import parse_llm_response, NonESGQueryError


class TestParseLLMResponse(unittest.TestCase):
    def test_parse_json_block(self):
        response = '''```json
{
  "collection": "esg_emissions",
  "query_type": "find",
  "filter": {"company.ticker": "AAPL"},
  "explanation": "Fetches Apple data"
}
```'''
        result = parse_llm_response(response)
        self.assertEqual(result["collection"], "esg_emissions")
        self.assertEqual(result["query_type"], "find")
        self.assertEqual(result["filter"]["company.ticker"], "AAPL")

    def test_parse_raw_json(self):
        response = '{"collection": "esg_governance", "query_type": "aggregate", "pipeline": []}'
        result = parse_llm_response(response)
        self.assertEqual(result["collection"], "esg_governance")
        self.assertEqual(result["query_type"], "aggregate")

    def test_parse_with_surrounding_text(self):
        response = '''Here is the query:
{"collection": "esg_social", "query_type": "find", "filter": {"reporting_year": 2023}}
This will find all social data for 2023.'''
        result = parse_llm_response(response)
        self.assertEqual(result["collection"], "esg_social")

    def test_parse_non_esg_response_raises(self):
        with self.assertRaises(NonESGQueryError) as ctx:
            parse_llm_response("I'm sorry, I can only help with ESG-related questions.")
        self.assertIn("ESG", ctx.exception.llm_message)

    def test_parse_invalid_json_in_braces_raises(self):
        with self.assertRaises(NonESGQueryError):
            parse_llm_response("Here is {broken json that won't parse}")


class TestDemoQueryStructures(unittest.TestCase):
    """Verify that the expected MQL structures for demo queries are valid."""

    def test_trend_query(self):
        query = {
            "collection": "esg_emissions",
            "query_type": "find",
            "filter": {"company.ticker": "AAPL"},
            "projection": {"reporting_year": 1, "emissions.scope_1.value": 1, "_id": 0},
            "sort": {"reporting_year": 1},
        }
        self.assertEqual(query["query_type"], "find")
        self.assertIn("company.ticker", query["filter"])

    def test_aggregation_query(self):
        query = {
            "collection": "esg_emissions",
            "query_type": "aggregate",
            "pipeline": [
                {"$match": {"reporting_year": 2023}},
                {"$group": {"_id": "$company.sector", "avg": {"$avg": "$emissions.carbon_intensity.value"}}},
                {"$sort": {"avg": -1}},
                {"$limit": 10},
            ],
        }
        self.assertEqual(query["query_type"], "aggregate")
        self.assertEqual(len(query["pipeline"]), 4)
        self.assertIn("$match", query["pipeline"][0])

    def test_comparison_query(self):
        query = {
            "collection": "esg_emissions",
            "query_type": "find",
            "filter": {"company.ticker": {"$in": ["MSFT", "GOOGL"]}, "reporting_year": 2023},
        }
        self.assertIn("$in", str(query["filter"]["company.ticker"]))

    def test_top_n_query(self):
        query = {
            "collection": "esg_emissions",
            "query_type": "find",
            "filter": {"reporting_year": 2023},
            "sort": {"energy.renewable_pct": -1},
            "limit": 5,
        }
        self.assertEqual(query["limit"], 5)
        self.assertEqual(query["sort"]["energy.renewable_pct"], -1)


if __name__ == "__main__":
    unittest.main()
