"""System prompts and few-shot examples for the ESG query agent."""

SYSTEM_PROMPT = """You are an ESG Data Assistant that translates natural language questions about Environmental, Social, and Governance data into MongoDB queries. You have access to three collections in a MongoDB database.

CRITICAL RULES:
1. ONLY use fields from the queryable_fields list provided in the schema context.
2. NEVER use $regex on any field.
3. Always use aggregation pipelines for grouping, averaging, ranking, or trend analysis.
4. Use find() only for simple lookups and filters.
5. Always include a filter in your queries — never query without one.
6. When filtering by company name, prefer using company.ticker if possible.
7. For "top N" queries, always include a $sort and $limit.
8. For trend queries, sort by reporting_year ascending.
9. When comparing companies, use $in for the ticker filter.
10. Return the collection name, query type (find or aggregate), and the query/pipeline.

COLLECTIONS:
- esg_emissions: Climate metrics, GHG emissions by scope, carbon intensity, energy data
- esg_governance: Board composition, policies, ESG scores/ratings, controversies
- esg_social: Workforce demographics, diversity, health/safety, community engagement

OUTPUT FORMAT:
You must respond with a JSON object containing:
{{
  "collection": "<collection_name>",
  "query_type": "find" | "aggregate",
  "filter": {{...}},          // for find queries
  "projection": {{...}},      // optional, for find queries
  "sort": {{...}},            // optional, for find queries
  "limit": <number>,          // optional, for find queries
  "pipeline": [...],          // for aggregate queries
  "explanation": "Brief explanation of what this query does"
}}

{schema_context}
"""

FEW_SHOT_EXAMPLES = [
    {
        "question": "How have Apple's emissions trended over 10 years?",
        "answer": """{
  "collection": "esg_emissions",
  "query_type": "find",
  "filter": {"company.ticker": "AAPL"},
  "projection": {"reporting_year": 1, "emissions.scope_1.value": 1, "emissions.scope_2.market_based.value": 1, "emissions.scope_3.total.value": 1, "emissions.total": 1, "_id": 0},
  "sort": {"reporting_year": 1},
  "explanation": "Retrieves Apple's emissions data across all years, sorted chronologically to show the trend."
}"""
    },
    {
        "question": "Which sector has the highest average carbon intensity?",
        "answer": """{
  "collection": "esg_emissions",
  "query_type": "aggregate",
  "pipeline": [
    {"$match": {"reporting_year": 2023}},
    {"$group": {"_id": "$company.sector", "avg_carbon_intensity": {"$avg": "$emissions.carbon_intensity.value"}}},
    {"$sort": {"avg_carbon_intensity": -1}},
    {"$limit": 10}
  ],
  "explanation": "Groups 2023 emissions by sector and calculates average carbon intensity, sorted highest first."
}"""
    },
    {
        "question": "Compare Microsoft and Google Scope 1 emissions in 2023",
        "answer": """{
  "collection": "esg_emissions",
  "query_type": "find",
  "filter": {"company.ticker": {"$in": ["MSFT", "GOOGL"]}, "reporting_year": 2023},
  "projection": {"company.name": 1, "company.ticker": 1, "emissions.scope_1.value": 1, "emissions.scope_2.market_based.value": 1, "emissions.total": 1, "_id": 0},
  "explanation": "Fetches emissions data for Microsoft and Alphabet for 2023 side-by-side comparison."
}"""
    },
    {
        "question": "Top 5 companies by renewable energy percentage",
        "answer": """{
  "collection": "esg_emissions",
  "query_type": "find",
  "filter": {"reporting_year": 2023},
  "projection": {"company.name": 1, "company.ticker": 1, "energy.renewable_pct": 1, "_id": 0},
  "sort": {"energy.renewable_pct": -1},
  "limit": 5,
  "explanation": "Finds the top 5 companies with the highest renewable energy percentage in 2023."
}"""
    },
    {
        "question": "Which companies have SBTi-aligned targets?",
        "answer": """{
  "collection": "esg_emissions",
  "query_type": "find",
  "filter": {"targets.sbti_aligned": true, "reporting_year": 2023},
  "projection": {"company.name": 1, "company.ticker": 1, "targets.net_zero_target_year": 1, "targets.reduction_target_pct": 1, "_id": 0},
  "explanation": "Lists all companies with SBTi-aligned targets for the most recent year."
}"""
    },
    {
        "question": "Which companies had controversies in 2023?",
        "answer": """{
  "collection": "esg_governance",
  "query_type": "find",
  "filter": {"controversies.count": {"$gt": 0}, "reporting_year": 2023},
  "projection": {"company.name": 1, "company.ticker": 1, "controversies": 1, "_id": 0},
  "sort": {"controversies.count": -1},
  "explanation": "Finds companies that had one or more controversies in 2023, sorted by number of controversies."
}"""
    },
    {
        "question": "Average ESG score by sector",
        "answer": """{
  "collection": "esg_governance",
  "query_type": "aggregate",
  "pipeline": [
    {"$match": {"reporting_year": 2023}},
    {"$group": {"_id": "$company.sector", "avg_score": {"$avg": "$esg_score.score"}, "count": {"$sum": 1}}},
    {"$sort": {"avg_score": -1}}
  ],
  "explanation": "Calculates the average ESG score per sector for 2023, sorted by highest average."
}"""
    },
    {
        "question": "Show me the board diversity trend for tech companies",
        "answer": """{
  "collection": "esg_governance",
  "query_type": "aggregate",
  "pipeline": [
    {"$match": {"company.sector": "Technology"}},
    {"$group": {"_id": "$reporting_year", "avg_gender_diversity": {"$avg": "$board.gender_diversity_pct"}, "avg_independent": {"$avg": "$board.independent_pct"}}},
    {"$sort": {"_id": 1}}
  ],
  "explanation": "Shows how board gender diversity and independence have changed over time for tech companies."
}"""
    },
]


def format_few_shot_messages() -> list[dict]:
    messages = []
    for ex in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": ex["question"]})
        messages.append({"role": "assistant", "content": ex["answer"]})
    return messages
