SECTORS = {
    "Technology": [
        "Consumer Electronics", "Software", "Semiconductors", "Cloud Computing",
        "IT Services", "Internet Services"
    ],
    "Energy": [
        "Oil & Gas Exploration", "Oil & Gas Refining", "Renewable Energy",
        "Energy Storage", "Natural Gas"
    ],
    "Finance": [
        "Commercial Banking", "Investment Banking", "Insurance",
        "Asset Management", "Fintech"
    ],
    "Healthcare": [
        "Pharmaceuticals", "Medical Devices", "Biotechnology",
        "Health Insurance", "Hospital Systems"
    ],
    "Consumer": [
        "Retail", "Food & Beverage", "Apparel", "E-Commerce",
        "Consumer Products"
    ],
    "Industrial": [
        "Aerospace & Defense", "Machinery", "Electrical Equipment",
        "Construction", "Transportation"
    ],
    "Materials": [
        "Chemicals", "Metals & Mining", "Paper & Packaging",
        "Construction Materials", "Steel"
    ],
    "Utilities": [
        "Electric Utilities", "Gas Utilities", "Water Utilities",
        "Multi-Utilities", "Renewable Utilities"
    ],
}

COMPANIES = [
    {"name": "Apple Inc.", "ticker": "AAPL", "sector": "Technology", "industry": "Consumer Electronics", "region": "North America", "country": "US"},
    {"name": "Microsoft Corporation", "ticker": "MSFT", "sector": "Technology", "industry": "Software", "region": "North America", "country": "US"},
    {"name": "Alphabet Inc.", "ticker": "GOOGL", "sector": "Technology", "industry": "Internet Services", "region": "North America", "country": "US"},
    {"name": "NVIDIA Corporation", "ticker": "NVDA", "sector": "Technology", "industry": "Semiconductors", "region": "North America", "country": "US"},
    {"name": "Samsung Electronics", "ticker": "005930.KS", "sector": "Technology", "industry": "Consumer Electronics", "region": "Asia Pacific", "country": "KR"},
    {"name": "Taiwan Semiconductor", "ticker": "TSM", "sector": "Technology", "industry": "Semiconductors", "region": "Asia Pacific", "country": "TW"},
    {"name": "ExxonMobil Corporation", "ticker": "XOM", "sector": "Energy", "industry": "Oil & Gas Exploration", "region": "North America", "country": "US"},
    {"name": "Chevron Corporation", "ticker": "CVX", "sector": "Energy", "industry": "Oil & Gas Refining", "region": "North America", "country": "US"},
    {"name": "Shell plc", "ticker": "SHEL", "sector": "Energy", "industry": "Oil & Gas Exploration", "region": "Europe", "country": "GB"},
    {"name": "TotalEnergies SE", "ticker": "TTE", "sector": "Energy", "industry": "Oil & Gas Refining", "region": "Europe", "country": "FR"},
    {"name": "NextEra Energy", "ticker": "NEE", "sector": "Energy", "industry": "Renewable Energy", "region": "North America", "country": "US"},
    {"name": "Enphase Energy", "ticker": "ENPH", "sector": "Energy", "industry": "Energy Storage", "region": "North America", "country": "US"},
    {"name": "JPMorgan Chase & Co.", "ticker": "JPM", "sector": "Finance", "industry": "Commercial Banking", "region": "North America", "country": "US"},
    {"name": "Goldman Sachs Group", "ticker": "GS", "sector": "Finance", "industry": "Investment Banking", "region": "North America", "country": "US"},
    {"name": "HSBC Holdings", "ticker": "HSBA", "sector": "Finance", "industry": "Commercial Banking", "region": "Europe", "country": "GB"},
    {"name": "Allianz SE", "ticker": "ALV", "sector": "Finance", "industry": "Insurance", "region": "Europe", "country": "DE"},
    {"name": "BlackRock Inc.", "ticker": "BLK", "sector": "Finance", "industry": "Asset Management", "region": "North America", "country": "US"},
    {"name": "Stripe Inc.", "ticker": "STRIPE", "sector": "Finance", "industry": "Fintech", "region": "North America", "country": "US"},
    {"name": "Johnson & Johnson", "ticker": "JNJ", "sector": "Healthcare", "industry": "Pharmaceuticals", "region": "North America", "country": "US"},
    {"name": "Pfizer Inc.", "ticker": "PFE", "sector": "Healthcare", "industry": "Pharmaceuticals", "region": "North America", "country": "US"},
    {"name": "Medtronic plc", "ticker": "MDT", "sector": "Healthcare", "industry": "Medical Devices", "region": "Europe", "country": "IE"},
    {"name": "Roche Holding AG", "ticker": "ROG", "sector": "Healthcare", "industry": "Biotechnology", "region": "Europe", "country": "CH"},
    {"name": "UnitedHealth Group", "ticker": "UNH", "sector": "Healthcare", "industry": "Health Insurance", "region": "North America", "country": "US"},
    {"name": "HCA Healthcare", "ticker": "HCA", "sector": "Healthcare", "industry": "Hospital Systems", "region": "North America", "country": "US"},
    {"name": "Amazon.com Inc.", "ticker": "AMZN", "sector": "Consumer", "industry": "E-Commerce", "region": "North America", "country": "US"},
    {"name": "Walmart Inc.", "ticker": "WMT", "sector": "Consumer", "industry": "Retail", "region": "North America", "country": "US"},
    {"name": "Nestle SA", "ticker": "NESN", "sector": "Consumer", "industry": "Food & Beverage", "region": "Europe", "country": "CH"},
    {"name": "Nike Inc.", "ticker": "NKE", "sector": "Consumer", "industry": "Apparel", "region": "North America", "country": "US"},
    {"name": "Procter & Gamble Co.", "ticker": "PG", "sector": "Consumer", "industry": "Consumer Products", "region": "North America", "country": "US"},
    {"name": "LVMH Moet Hennessy", "ticker": "MC", "sector": "Consumer", "industry": "Apparel", "region": "Europe", "country": "FR"},
    {"name": "Boeing Company", "ticker": "BA", "sector": "Industrial", "industry": "Aerospace & Defense", "region": "North America", "country": "US"},
    {"name": "Caterpillar Inc.", "ticker": "CAT", "sector": "Industrial", "industry": "Machinery", "region": "North America", "country": "US"},
    {"name": "Siemens AG", "ticker": "SIE", "sector": "Industrial", "industry": "Electrical Equipment", "region": "Europe", "country": "DE"},
    {"name": "Vinci SA", "ticker": "DG", "sector": "Industrial", "industry": "Construction", "region": "Europe", "country": "FR"},
    {"name": "Union Pacific Corp.", "ticker": "UNP", "sector": "Industrial", "industry": "Transportation", "region": "North America", "country": "US"},
    {"name": "Honeywell International", "ticker": "HON", "sector": "Industrial", "industry": "Electrical Equipment", "region": "North America", "country": "US"},
    {"name": "BASF SE", "ticker": "BAS", "sector": "Materials", "industry": "Chemicals", "region": "Europe", "country": "DE"},
    {"name": "Rio Tinto Group", "ticker": "RIO", "sector": "Materials", "industry": "Metals & Mining", "region": "Europe", "country": "GB"},
    {"name": "BHP Group", "ticker": "BHP", "sector": "Materials", "industry": "Metals & Mining", "region": "Asia Pacific", "country": "AU"},
    {"name": "International Paper", "ticker": "IP", "sector": "Materials", "industry": "Paper & Packaging", "region": "North America", "country": "US"},
    {"name": "LafargeHolcim", "ticker": "LHN", "sector": "Materials", "industry": "Construction Materials", "region": "Europe", "country": "CH"},
    {"name": "ArcelorMittal", "ticker": "MT", "sector": "Materials", "industry": "Steel", "region": "Europe", "country": "LU"},
    {"name": "Duke Energy Corp.", "ticker": "DUK", "sector": "Utilities", "industry": "Electric Utilities", "region": "North America", "country": "US"},
    {"name": "Southern Company", "ticker": "SO", "sector": "Utilities", "industry": "Electric Utilities", "region": "North America", "country": "US"},
    {"name": "National Grid plc", "ticker": "NG", "sector": "Utilities", "industry": "Multi-Utilities", "region": "Europe", "country": "GB"},
    {"name": "Enel SpA", "ticker": "ENEL", "sector": "Utilities", "industry": "Renewable Utilities", "region": "Europe", "country": "IT"},
    {"name": "American Water Works", "ticker": "AWK", "sector": "Utilities", "industry": "Water Utilities", "region": "North America", "country": "US"},
    {"name": "Sempra Energy", "ticker": "SRE", "sector": "Utilities", "industry": "Gas Utilities", "region": "North America", "country": "US"},
    {"name": "Iberdrola SA", "ticker": "IBE", "sector": "Utilities", "industry": "Renewable Utilities", "region": "Europe", "country": "ES"},
    {"name": "Orsted A/S", "ticker": "ORSTED", "sector": "Utilities", "industry": "Renewable Utilities", "region": "Europe", "country": "DK"},
]

REPORTING_YEARS = list(range(2014, 2024))

REPORTING_FRAMEWORKS = ["GHG Protocol", "TCFD", "SASB", "GRI", "CDP"]

RENEWABLE_SOURCES = ["solar", "wind", "biogas", "hydro", "geothermal"]

DATA_SOURCES = ["CDP", "Bloomberg", "MSCI", "Sustainalytics", "Company Filing", "Refinitiv"]

VERIFIERS = ["Deloitte", "PwC", "EY", "KPMG", "Bureau Veritas", "SGS"]

ESG_RATING_SCALE = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]

ESG_SCORE_RANGES = {
    "AAA": (8.5, 10.0),
    "AA": (7.0, 8.49),
    "A": (5.7, 6.99),
    "BBB": (4.3, 5.69),
    "BB": (2.9, 4.29),
    "B": (1.4, 2.89),
    "CCC": (0.0, 1.39),
}

ESG_PROVIDERS = ["MSCI", "Sustainalytics", "S&P Global", "Refinitiv", "Bloomberg"]

CONTROVERSY_CATEGORIES = [
    "labor_practices", "data_privacy", "environmental_violation",
    "corruption", "human_rights", "product_safety",
    "tax_avoidance", "antitrust", "supply_chain",
    "executive_compensation"
]

CONTROVERSY_SEVERITIES = ["low", "moderate", "severe", "critical"]

SECTOR_EMISSION_PROFILES = {
    "Technology": {"base_scope1": (10000, 80000), "base_scope2_market": (0, 50000), "base_scope3_total": (5000000, 30000000), "renewable_tendency": "high"},
    "Energy": {"base_scope1": (5000000, 50000000), "base_scope2_market": (500000, 5000000), "base_scope3_total": (50000000, 500000000), "renewable_tendency": "low"},
    "Finance": {"base_scope1": (5000, 30000), "base_scope2_market": (10000, 80000), "base_scope3_total": (1000000, 20000000), "renewable_tendency": "medium"},
    "Healthcare": {"base_scope1": (20000, 150000), "base_scope2_market": (30000, 200000), "base_scope3_total": (2000000, 15000000), "renewable_tendency": "medium"},
    "Consumer": {"base_scope1": (50000, 500000), "base_scope2_market": (20000, 300000), "base_scope3_total": (10000000, 100000000), "renewable_tendency": "medium"},
    "Industrial": {"base_scope1": (200000, 2000000), "base_scope2_market": (100000, 800000), "base_scope3_total": (5000000, 50000000), "renewable_tendency": "low"},
    "Materials": {"base_scope1": (1000000, 20000000), "base_scope2_market": (500000, 5000000), "base_scope3_total": (10000000, 100000000), "renewable_tendency": "low"},
    "Utilities": {"base_scope1": (2000000, 30000000), "base_scope2_market": (100000, 1000000), "base_scope3_total": (5000000, 50000000), "renewable_tendency": "medium"},
}

SECTOR_EMPLOYEE_RANGES = {
    "Technology": (5000, 200000),
    "Energy": (10000, 100000),
    "Finance": (20000, 300000),
    "Healthcare": (15000, 350000),
    "Consumer": (30000, 2200000),
    "Industrial": (20000, 170000),
    "Materials": (15000, 200000),
    "Utilities": (10000, 80000),
}

SECTOR_REVENUE_RANGES_USD = {
    "Technology": (20_000_000_000, 400_000_000_000),
    "Energy": (30_000_000_000, 500_000_000_000),
    "Finance": (10_000_000_000, 200_000_000_000),
    "Healthcare": (15_000_000_000, 300_000_000_000),
    "Consumer": (20_000_000_000, 600_000_000_000),
    "Industrial": (10_000_000_000, 150_000_000_000),
    "Materials": (10_000_000_000, 100_000_000_000),
    "Utilities": (10_000_000_000, 80_000_000_000),
}
