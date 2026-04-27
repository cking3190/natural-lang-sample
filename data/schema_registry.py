"""Phase 2: Build esg_schema_registry collection with rich metadata for LLM context."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DATABASE, COLLECTIONS
from data.constants import (
    SECTORS, REPORTING_FRAMEWORKS, RENEWABLE_SOURCES, ESG_RATING_SCALE,
    ESG_PROVIDERS, CONTROVERSY_CATEGORIES, CONTROVERSY_SEVERITIES, DATA_SOURCES,
)

EMISSIONS_REGISTRY = {
    "collection_name": "esg_emissions",
    "description": (
        "Climate and environmental metrics including greenhouse gas emissions by scope, "
        "carbon intensity, energy consumption, and reduction targets. "
        "One document per company per reporting year."
    ),
    "field_descriptions": {
        "company.name": "Full legal name of the company",
        "company.ticker": "Stock ticker symbol (e.g., AAPL, MSFT)",
        "company.sector": "Business sector classification",
        "company.industry": "Specific industry within the sector",
        "company.region": "Geographic region (North America, Europe, Asia Pacific)",
        "company.country": "ISO country code",
        "reporting_year": "Year the data covers (2014-2023)",
        "reporting_framework": "ESG reporting framework used",
        "emissions.scope_1.value": "Direct GHG emissions in tonnes CO2 equivalent",
        "emissions.scope_1.verified": "Whether scope 1 emissions have been third-party verified",
        "emissions.scope_2.market_based.value": "Indirect emissions from purchased energy (market-based method) in tCO2e",
        "emissions.scope_2.location_based.value": "Indirect emissions from purchased energy (location-based method) in tCO2e",
        "emissions.scope_3.total.value": "Total upstream and downstream value chain emissions in tCO2e",
        "emissions.total": "Sum of all scope emissions in tCO2e",
        "emissions.carbon_intensity.value": "Emissions per million dollars of revenue (tCO2e/M$ revenue)",
        "emissions.carbon_intensity.revenue_base_usd": "Revenue base used for carbon intensity calculation in USD",
        "targets.net_zero_target_year": "Year the company aims to reach net zero (null if no target)",
        "targets.sbti_aligned": "Whether the company has Science Based Targets initiative aligned targets",
        "targets.reduction_target_pct": "Percentage emission reduction target",
        "targets.baseline_year": "Baseline year for reduction target",
        "energy.total_consumption_mwh": "Total energy consumption in megawatt-hours",
        "energy.renewable_pct": "Percentage of energy from renewable sources",
        "energy.renewable_sources": "Types of renewable energy sources used",
        "metadata.data_source": "Source of the ESG data",
        "metadata.last_updated": "Date the record was last updated",
        "metadata.confidence_score": "Data quality confidence score (0-1)",
    },
    "enum_values": {
        "company.sector": list(SECTORS.keys()),
        "company.region": ["North America", "Europe", "Asia Pacific"],
        "reporting_framework": REPORTING_FRAMEWORKS,
        "energy.renewable_sources": RENEWABLE_SOURCES,
        "metadata.data_source": DATA_SOURCES,
    },
    "queryable_fields": [
        "company.name", "company.ticker", "company.sector", "company.industry",
        "company.region", "company.country", "reporting_year", "reporting_framework",
        "emissions.scope_1.value", "emissions.scope_1.verified",
        "emissions.scope_2.market_based.value", "emissions.scope_2.location_based.value",
        "emissions.scope_3.total.value", "emissions.total",
        "emissions.carbon_intensity.value", "emissions.carbon_intensity.revenue_base_usd",
        "targets.net_zero_target_year", "targets.sbti_aligned",
        "targets.reduction_target_pct",
        "energy.total_consumption_mwh", "energy.renewable_pct",
    ],
    "common_query_patterns": [
        "Trend over time: filter by ticker, sort by reporting_year, project emissions fields",
        "Sector comparison: group by sector, aggregate emissions metrics",
        "Top N emitters: sort by emissions.total descending, limit N",
        "Year-over-year change: use $setWindowFields or application-side calculation",
        "Carbon intensity ranking: sort by emissions.carbon_intensity.value",
        "Renewable energy leaders: sort by energy.renewable_pct descending",
    ],
}

GOVERNANCE_REGISTRY = {
    "collection_name": "esg_governance",
    "description": (
        "Board composition, corporate policies, ESG scores/ratings, and controversy records. "
        "One document per company per reporting year."
    ),
    "field_descriptions": {
        "company.name": "Full legal name of the company",
        "company.ticker": "Stock ticker symbol",
        "company.sector": "Business sector classification",
        "company.industry": "Specific industry within the sector",
        "company.region": "Geographic region",
        "company.country": "ISO country code",
        "reporting_year": "Year the data covers (2014-2023)",
        "board.total_members": "Total number of board members",
        "board.independent_pct": "Percentage of independent board members",
        "board.gender_diversity_pct": "Percentage of women on the board",
        "board.avg_tenure_years": "Average tenure of board members in years",
        "board.esg_committee": "Whether the board has a dedicated ESG committee",
        "board.separate_chair_ceo": "Whether the board chair and CEO are separate people",
        "policies.anti_corruption": "Whether the company has an anti-corruption policy",
        "policies.whistleblower_protection": "Whether the company has whistleblower protection",
        "policies.human_rights_policy": "Whether the company has a human rights policy",
        "policies.supply_chain_due_diligence": "Whether the company conducts supply chain due diligence",
        "policies.political_contributions_disclosed": "Whether political contributions are disclosed",
        "controversies.count": "Number of controversies in the reporting year",
        "controversies.severity": "Severity level of the most severe controversy",
        "controversies.categories": "Categories of controversies",
        "esg_score.provider": "ESG rating provider name",
        "esg_score.rating": "ESG letter rating (AAA to CCC)",
        "esg_score.score": "Numerical ESG score (0-10)",
        "esg_score.percentile": "Percentile ranking among peers",
    },
    "enum_values": {
        "company.sector": list(SECTORS.keys()),
        "esg_score.rating": ESG_RATING_SCALE,
        "esg_score.provider": ESG_PROVIDERS,
        "controversies.severity": CONTROVERSY_SEVERITIES,
        "controversies.categories": CONTROVERSY_CATEGORIES,
    },
    "queryable_fields": [
        "company.name", "company.ticker", "company.sector", "company.industry",
        "company.region", "company.country", "reporting_year",
        "board.total_members", "board.independent_pct", "board.gender_diversity_pct",
        "board.avg_tenure_years", "board.esg_committee", "board.separate_chair_ceo",
        "policies.anti_corruption", "policies.whistleblower_protection",
        "policies.human_rights_policy", "policies.supply_chain_due_diligence",
        "policies.political_contributions_disclosed",
        "controversies.count", "controversies.severity", "controversies.categories",
        "esg_score.provider", "esg_score.rating", "esg_score.score", "esg_score.percentile",
    ],
    "common_query_patterns": [
        "ESG score ranking: sort by esg_score.score descending",
        "Sector average ESG: group by sector, average score",
        "Board diversity trend: filter by ticker, sort by year, project board fields",
        "Controversy search: filter by controversies.count > 0",
        "Policy compliance: filter by specific policy fields = true",
        "Rating distribution: group by esg_score.rating, count",
    ],
}

SOCIAL_REGISTRY = {
    "collection_name": "esg_social",
    "description": (
        "Workforce demographics, diversity metrics, health and safety statistics, "
        "and community engagement data. One document per company per reporting year."
    ),
    "field_descriptions": {
        "company.name": "Full legal name of the company",
        "company.ticker": "Stock ticker symbol",
        "company.sector": "Business sector classification",
        "company.industry": "Specific industry within the sector",
        "company.region": "Geographic region",
        "company.country": "ISO country code",
        "reporting_year": "Year the data covers (2014-2023)",
        "workforce.total_employees": "Total number of employees",
        "workforce.gender_pay_gap_pct": "Gender pay gap as a percentage",
        "workforce.diversity.women_pct": "Percentage of women in the workforce",
        "workforce.diversity.underrepresented_minorities_pct": "Percentage of underrepresented minorities",
        "workforce.diversity.women_in_leadership_pct": "Percentage of women in leadership positions",
        "workforce.turnover_rate_pct": "Annual employee turnover rate as a percentage",
        "workforce.training_hours_per_employee": "Average training hours per employee per year",
        "health_safety.injury_rate": "Workplace injury rate",
        "health_safety.fatalities": "Number of workplace fatalities",
        "health_safety.lost_time_injury_freq": "Lost time injury frequency rate",
        "community.charitable_giving_usd": "Total charitable giving in USD",
        "community.volunteer_hours": "Total employee volunteer hours",
    },
    "enum_values": {
        "company.sector": list(SECTORS.keys()),
    },
    "queryable_fields": [
        "company.name", "company.ticker", "company.sector", "company.industry",
        "company.region", "company.country", "reporting_year",
        "workforce.total_employees", "workforce.gender_pay_gap_pct",
        "workforce.diversity.women_pct", "workforce.diversity.underrepresented_minorities_pct",
        "workforce.diversity.women_in_leadership_pct",
        "workforce.turnover_rate_pct", "workforce.training_hours_per_employee",
        "health_safety.injury_rate", "health_safety.fatalities",
        "health_safety.lost_time_injury_freq",
        "community.charitable_giving_usd", "community.volunteer_hours",
    ],
    "common_query_patterns": [
        "Diversity ranking: sort by workforce.diversity.women_pct descending",
        "Pay gap analysis: sort by workforce.gender_pay_gap_pct",
        "Safety record: filter by health_safety.fatalities > 0",
        "Community impact: sort by community.charitable_giving_usd descending",
        "Workforce size comparison: group by sector, average total_employees",
        "Training investment: sort by workforce.training_hours_per_employee descending",
    ],
}


def build_registry(uri=None, db_name=None):
    client = MongoClient(uri or MONGODB_URI)
    db = client[db_name or MONGODB_DATABASE]

    registry_coll = db[COLLECTIONS["schema_registry"]]
    registry_coll.drop()

    registries = [EMISSIONS_REGISTRY, GOVERNANCE_REGISTRY, SOCIAL_REGISTRY]

    for reg in registries:
        coll_name = reg["collection_name"]
        coll = db[coll_name]

        sample_docs = list(coll.find().limit(3))
        for doc in sample_docs:
            doc["_id"] = str(doc["_id"])
        reg["sample_documents"] = sample_docs

        indexes = []
        for idx_info in coll.list_indexes():
            if idx_info["name"] == "_id_":
                continue
            indexes.append({"keys": dict(idx_info["key"]), "name": idx_info["name"]})
        reg["indexes"] = indexes

    registry_coll.insert_many(registries)
    print(f"Built schema registry with {len(registries)} collection entries.")

    for reg in registries:
        print(f"  - {reg['collection_name']}: {len(reg['queryable_fields'])} queryable fields, "
              f"{len(reg['indexes'])} indexes, {len(reg['sample_documents'])} sample docs")

    client.close()


if __name__ == "__main__":
    build_registry()
