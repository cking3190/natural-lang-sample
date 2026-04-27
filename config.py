import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/?directConnection=true")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "esg_demo")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

MAX_QUERY_TIME_MS = int(os.getenv("MAX_QUERY_TIME_MS", "5000"))
MAX_RESULT_LIMIT = int(os.getenv("MAX_RESULT_LIMIT", "1000"))

COLLECTIONS = {
    "emissions": "esg_emissions",
    "governance": "esg_governance",
    "social": "esg_social",
    "schema_registry": "esg_schema_registry",
    "audit_log": "esg_query_audit",
}
