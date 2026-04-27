"""Phase 1: Synthetic ESG data generator. Idempotent — drops and recreates collections."""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from pymongo import MongoClient, IndexModel, ASCENDING
from data.constants import (
    COMPANIES, REPORTING_YEARS, REPORTING_FRAMEWORKS, RENEWABLE_SOURCES,
    DATA_SOURCES, VERIFIERS, ESG_RATING_SCALE, ESG_SCORE_RANGES, ESG_PROVIDERS,
    CONTROVERSY_CATEGORIES, CONTROVERSY_SEVERITIES, SECTOR_EMISSION_PROFILES,
    SECTOR_EMPLOYEE_RANGES, SECTOR_REVENUE_RANGES_USD,
)
from config import MONGODB_URI, MONGODB_DATABASE, COLLECTIONS

random.seed(42)


def _rand_range(low, high):
    return random.uniform(low, high)


def _year_factor(year, base_year=2014, direction="down", strength=0.04):
    """Return a multiplier that trends up or down from base_year."""
    elapsed = year - base_year
    if direction == "down":
        return max(0.3, 1.0 - elapsed * strength * random.uniform(0.5, 1.5))
    return min(2.0, 1.0 + elapsed * strength * random.uniform(0.5, 1.5))


def _assign_rating(score):
    for rating, (low, high) in ESG_SCORE_RANGES.items():
        if low <= score <= high:
            return rating
    return "BBB"


def generate_emissions_doc(company, year, company_seed):
    sector = company["sector"]
    profile = SECTOR_EMISSION_PROFILES[sector]
    rng = random.Random(company_seed + year)

    has_sbti = rng.random() > 0.4
    reduction_factor = _year_factor(year, direction="down", strength=0.05 if has_sbti else 0.02)

    base_s1 = rng.uniform(*profile["base_scope1"])
    base_s2 = rng.uniform(*profile["base_scope2_market"])
    base_s3 = rng.uniform(*profile["base_scope3_total"])

    scope1_val = round(base_s1 * reduction_factor)
    scope2_market = round(base_s2 * reduction_factor)
    scope2_location = round(scope2_market * rng.uniform(1.5, 3.0))
    scope3_total = round(base_s3 * reduction_factor * rng.uniform(0.85, 1.15))

    s3_purchased = round(scope3_total * rng.uniform(0.55, 0.75))
    s3_transport = round(scope3_total * rng.uniform(0.05, 0.15))
    s3_products = round(scope3_total * rng.uniform(0.08, 0.18))
    s3_travel = round(scope3_total * rng.uniform(0.005, 0.02))
    s3_commute = round(scope3_total * rng.uniform(0.003, 0.015))

    total_emissions = scope1_val + scope2_market + scope3_total
    rev_range = SECTOR_REVENUE_RANGES_USD[sector]
    revenue = rng.uniform(*rev_range) * _year_factor(year, direction="up", strength=0.03)

    renewable_tendency = {"high": 0.7, "medium": 0.4, "low": 0.15}[profile["renewable_tendency"]]
    base_renewable = renewable_tendency * 100
    renewable_pct = min(100, round(base_renewable * _year_factor(year, direction="up", strength=0.04), 1))

    chosen_sources = rng.sample(RENEWABLE_SOURCES, k=rng.randint(1, min(3, len(RENEWABLE_SOURCES))))

    return {
        "company": {
            "name": company["name"],
            "ticker": company["ticker"],
            "sector": company["sector"],
            "industry": company["industry"],
            "region": company["region"],
            "country": company["country"],
        },
        "reporting_year": year,
        "reporting_framework": rng.choice(REPORTING_FRAMEWORKS),
        "emissions": {
            "scope_1": {
                "value": scope1_val,
                "unit": "tCO2e",
                "verified": rng.random() > 0.2,
                "verifier": rng.choice(VERIFIERS),
            },
            "scope_2": {
                "market_based": {"value": scope2_market, "unit": "tCO2e"},
                "location_based": {"value": scope2_location, "unit": "tCO2e"},
            },
            "scope_3": {
                "total": {"value": scope3_total, "unit": "tCO2e"},
                "categories": {
                    "purchased_goods": s3_purchased,
                    "transportation": s3_transport,
                    "use_of_sold_products": s3_products,
                    "business_travel": s3_travel,
                    "employee_commuting": s3_commute,
                },
            },
            "total": total_emissions,
            "carbon_intensity": {
                "value": round(total_emissions / (revenue / 1_000_000), 1),
                "unit": "tCO2e/M$ revenue",
                "revenue_base_usd": round(revenue),
            },
        },
        "targets": {
            "net_zero_target_year": rng.choice([2030, 2035, 2040, 2050]) if has_sbti else None,
            "sbti_aligned": has_sbti,
            "reduction_target_pct": rng.choice([50, 60, 75, 80, 90]) if has_sbti else None,
            "baseline_year": 2015 if has_sbti else None,
        },
        "energy": {
            "total_consumption_mwh": round(rng.uniform(100000, 5000000)),
            "renewable_pct": renewable_pct,
            "renewable_sources": chosen_sources,
        },
        "metadata": {
            "data_source": rng.choice(DATA_SOURCES),
            "last_updated": f"{year + 1}-{rng.randint(1,6):02d}-{rng.randint(1,28):02d}",
            "confidence_score": round(rng.uniform(0.7, 0.99), 2),
        },
    }


def generate_governance_doc(company, year, company_seed):
    rng = random.Random(company_seed + year + 1000)
    sector = company["sector"]

    board_size = rng.randint(7, 15)
    diversity_trend = _year_factor(year, direction="up", strength=0.03)
    independent_pct = min(100, round(rng.uniform(50, 75) * diversity_trend, 1))
    gender_diversity = min(50, round(rng.uniform(15, 35) * diversity_trend, 1))

    controversy_count = rng.choices([0, 1, 2, 3, 4], weights=[40, 25, 20, 10, 5])[0]
    categories = rng.sample(CONTROVERSY_CATEGORIES, k=min(controversy_count, len(CONTROVERSY_CATEGORIES))) if controversy_count > 0 else []

    base_score = rng.uniform(3.0, 9.5)
    score_adj = _year_factor(year, direction="up", strength=0.02)
    esg_score = min(10.0, round(base_score * score_adj - controversy_count * 0.3, 1))
    esg_score = max(0.0, esg_score)
    rating = _assign_rating(esg_score)
    percentile = round(esg_score * 10 + rng.uniform(-3, 3), 0)
    percentile = max(1, min(99, percentile))

    return {
        "company": {
            "name": company["name"],
            "ticker": company["ticker"],
            "sector": company["sector"],
            "industry": company["industry"],
            "region": company["region"],
            "country": company["country"],
        },
        "reporting_year": year,
        "board": {
            "total_members": board_size,
            "independent_pct": independent_pct,
            "gender_diversity_pct": gender_diversity,
            "avg_tenure_years": round(rng.uniform(3, 12), 1),
            "esg_committee": rng.random() > 0.3,
            "separate_chair_ceo": rng.random() > 0.4,
        },
        "policies": {
            "anti_corruption": rng.random() > 0.1,
            "whistleblower_protection": rng.random() > 0.15,
            "human_rights_policy": rng.random() > 0.2,
            "supply_chain_due_diligence": rng.random() > 0.3,
            "political_contributions_disclosed": rng.random() > 0.4,
        },
        "controversies": {
            "count": controversy_count,
            "severity": rng.choice(CONTROVERSY_SEVERITIES) if controversy_count > 0 else None,
            "categories": categories,
        },
        "esg_score": {
            "provider": rng.choice(ESG_PROVIDERS),
            "rating": rating,
            "score": esg_score,
            "percentile": int(percentile),
        },
    }


def generate_social_doc(company, year, company_seed):
    rng = random.Random(company_seed + year + 2000)
    sector = company["sector"]

    emp_range = SECTOR_EMPLOYEE_RANGES[sector]
    base_employees = rng.uniform(*emp_range)
    employees = round(base_employees * _year_factor(year, direction="up", strength=0.02))

    diversity_trend = _year_factor(year, direction="up", strength=0.025)

    return {
        "company": {
            "name": company["name"],
            "ticker": company["ticker"],
            "sector": company["sector"],
            "industry": company["industry"],
            "region": company["region"],
            "country": company["country"],
        },
        "reporting_year": year,
        "workforce": {
            "total_employees": employees,
            "gender_pay_gap_pct": max(0, round(rng.uniform(1, 12) * _year_factor(year, direction="down", strength=0.03), 1)),
            "diversity": {
                "women_pct": min(50, round(rng.uniform(20, 40) * diversity_trend, 1)),
                "underrepresented_minorities_pct": min(50, round(rng.uniform(10, 35) * diversity_trend, 1)),
                "women_in_leadership_pct": min(50, round(rng.uniform(15, 35) * diversity_trend, 1)),
            },
            "turnover_rate_pct": round(rng.uniform(5, 25), 1),
            "training_hours_per_employee": round(rng.uniform(10, 80), 0),
        },
        "health_safety": {
            "injury_rate": round(rng.uniform(0.1, 5.0) * _year_factor(year, direction="down", strength=0.03), 1),
            "fatalities": rng.choices([0, 0, 0, 0, 1], weights=[80, 10, 5, 4, 1])[0],
            "lost_time_injury_freq": round(rng.uniform(0.05, 3.0), 2),
        },
        "community": {
            "charitable_giving_usd": round(rng.uniform(1_000_000, 500_000_000)),
            "volunteer_hours": round(rng.uniform(10000, 2000000)),
        },
    }


def create_indexes(db):
    emissions = db[COLLECTIONS["emissions"]]
    governance = db[COLLECTIONS["governance"]]
    social = db[COLLECTIONS["social"]]

    emissions.create_indexes([
        IndexModel([("company.ticker", ASCENDING), ("reporting_year", ASCENDING)], name="ticker_year"),
        IndexModel([("company.sector", ASCENDING)], name="sector"),
        IndexModel([("reporting_year", ASCENDING)], name="year"),
        IndexModel([("emissions.scope_1.value", ASCENDING)], name="scope1_value"),
        IndexModel([("emissions.total", ASCENDING)], name="total_emissions"),
        IndexModel([("energy.renewable_pct", ASCENDING)], name="renewable_pct"),
        IndexModel([("targets.sbti_aligned", ASCENDING)], name="sbti_aligned"),
    ])

    governance.create_indexes([
        IndexModel([("company.ticker", ASCENDING), ("reporting_year", ASCENDING)], name="ticker_year"),
        IndexModel([("company.sector", ASCENDING)], name="sector"),
        IndexModel([("reporting_year", ASCENDING)], name="year"),
        IndexModel([("esg_score.rating", ASCENDING)], name="esg_rating"),
        IndexModel([("esg_score.score", ASCENDING)], name="esg_score"),
        IndexModel([("controversies.count", ASCENDING)], name="controversy_count"),
        IndexModel([("board.gender_diversity_pct", ASCENDING)], name="board_diversity"),
    ])

    social.create_indexes([
        IndexModel([("company.ticker", ASCENDING), ("reporting_year", ASCENDING)], name="ticker_year"),
        IndexModel([("company.sector", ASCENDING)], name="sector"),
        IndexModel([("reporting_year", ASCENDING)], name="year"),
        IndexModel([("workforce.total_employees", ASCENDING)], name="total_employees"),
        IndexModel([("workforce.diversity.women_pct", ASCENDING)], name="women_pct"),
    ])


def run(uri=None, db_name=None):
    client = MongoClient(uri or MONGODB_URI)
    db = client[db_name or MONGODB_DATABASE]

    for coll_key in ["emissions", "governance", "social"]:
        db[COLLECTIONS[coll_key]].drop()
    print("Dropped existing collections.")

    emissions_docs = []
    governance_docs = []
    social_docs = []

    for idx, company in enumerate(COMPANIES):
        company_seed = idx * 10000
        for year in REPORTING_YEARS:
            emissions_docs.append(generate_emissions_doc(company, year, company_seed))
            governance_docs.append(generate_governance_doc(company, year, company_seed))
            social_docs.append(generate_social_doc(company, year, company_seed))

    db[COLLECTIONS["emissions"]].insert_many(emissions_docs)
    db[COLLECTIONS["governance"]].insert_many(governance_docs)
    db[COLLECTIONS["social"]].insert_many(social_docs)

    create_indexes(db)

    print(f"Inserted {len(emissions_docs)} docs into {COLLECTIONS['emissions']}")
    print(f"Inserted {len(governance_docs)} docs into {COLLECTIONS['governance']}")
    print(f"Inserted {len(social_docs)} docs into {COLLECTIONS['social']}")
    print(f"Total documents: {len(emissions_docs) + len(governance_docs) + len(social_docs)}")
    print(f"Companies: {len(COMPANIES)}, Years: {len(REPORTING_YEARS)}")
    print("Indexes created successfully.")

    client.close()


if __name__ == "__main__":
    run()
