"""Unit tests for the data generator — validates data shape and structure."""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.constants import COMPANIES, REPORTING_YEARS, SECTORS
from data.data_generator import generate_emissions_doc, generate_governance_doc, generate_social_doc


class TestEmissionsDoc(unittest.TestCase):
    def setUp(self):
        self.company = COMPANIES[0]  # Apple
        self.doc = generate_emissions_doc(self.company, 2023, 0)

    def test_company_fields(self):
        self.assertEqual(self.doc["company"]["ticker"], "AAPL")
        self.assertEqual(self.doc["company"]["name"], "Apple Inc.")
        self.assertIn(self.doc["company"]["sector"], SECTORS.keys())

    def test_emissions_structure(self):
        em = self.doc["emissions"]
        self.assertIn("scope_1", em)
        self.assertIn("scope_2", em)
        self.assertIn("scope_3", em)
        self.assertIn("total", em)
        self.assertIn("carbon_intensity", em)
        self.assertIsInstance(em["scope_1"]["value"], int)
        self.assertGreater(em["total"], 0)

    def test_targets_structure(self):
        t = self.doc["targets"]
        self.assertIn("sbti_aligned", t)
        self.assertIsInstance(t["sbti_aligned"], bool)

    def test_energy_structure(self):
        e = self.doc["energy"]
        self.assertIn("renewable_pct", e)
        self.assertGreaterEqual(e["renewable_pct"], 0)
        self.assertLessEqual(e["renewable_pct"], 100)
        self.assertIsInstance(e["renewable_sources"], list)

    def test_reporting_year(self):
        self.assertEqual(self.doc["reporting_year"], 2023)


class TestGovernanceDoc(unittest.TestCase):
    def setUp(self):
        self.doc = generate_governance_doc(COMPANIES[0], 2023, 0)

    def test_board_structure(self):
        b = self.doc["board"]
        self.assertIn("total_members", b)
        self.assertIn("independent_pct", b)
        self.assertIn("gender_diversity_pct", b)
        self.assertGreater(b["total_members"], 0)

    def test_esg_score_structure(self):
        s = self.doc["esg_score"]
        self.assertIn("rating", s)
        self.assertIn("score", s)
        self.assertIn("percentile", s)
        self.assertGreaterEqual(s["score"], 0)
        self.assertLessEqual(s["score"], 10)

    def test_controversies_structure(self):
        c = self.doc["controversies"]
        self.assertIn("count", c)
        self.assertIsInstance(c["count"], int)
        self.assertIsInstance(c["categories"], list)


class TestSocialDoc(unittest.TestCase):
    def setUp(self):
        self.doc = generate_social_doc(COMPANIES[0], 2023, 0)

    def test_workforce_structure(self):
        w = self.doc["workforce"]
        self.assertIn("total_employees", w)
        self.assertIn("diversity", w)
        self.assertIn("gender_pay_gap_pct", w)
        self.assertGreater(w["total_employees"], 0)

    def test_diversity_structure(self):
        d = self.doc["workforce"]["diversity"]
        self.assertIn("women_pct", d)
        self.assertIn("underrepresented_minorities_pct", d)
        self.assertIn("women_in_leadership_pct", d)

    def test_health_safety_structure(self):
        h = self.doc["health_safety"]
        self.assertIn("injury_rate", h)
        self.assertIn("fatalities", h)

    def test_community_structure(self):
        c = self.doc["community"]
        self.assertIn("charitable_giving_usd", c)
        self.assertIn("volunteer_hours", c)


class TestDataVolume(unittest.TestCase):
    def test_company_count(self):
        self.assertEqual(len(COMPANIES), 50)

    def test_year_range(self):
        self.assertEqual(len(REPORTING_YEARS), 10)
        self.assertEqual(REPORTING_YEARS[0], 2014)
        self.assertEqual(REPORTING_YEARS[-1], 2023)

    def test_expected_document_count(self):
        expected = len(COMPANIES) * len(REPORTING_YEARS) * 3
        self.assertEqual(expected, 1500)


if __name__ == "__main__":
    unittest.main()
