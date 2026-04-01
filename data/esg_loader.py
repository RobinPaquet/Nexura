import json
import os
from typing import Optional
from functools import lru_cache

def _get_esg_data_path() -> str:
    path = os.getenv("ESG_DATA_PATH")
    if not path:
        # Fallback: look for companies.json bundled in the repo (data/ directory)
        bundled = os.path.join(os.path.dirname(__file__), "companies.json")
        if os.path.exists(bundled):
            return bundled
        raise EnvironmentError(
            "ESG_DATA_PATH environment variable is not set and no bundled companies.json found. "
            "Copy .env.example to .env and set the path to companies.json."
        )
    return path

@lru_cache(maxsize=1)
def load_companies() -> list[dict]:
    path = _get_esg_data_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(
            f"ESG data file not found at '{path}'. "
            "Check that ESG_DATA_PATH points to a valid companies.json file."
        )
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ESG data file at '{path}': {e}")

def get_company_by_isin(isin: str) -> Optional[dict]:
    companies = load_companies()
    for company in companies:
        if company.get("isin") == isin or company.get("ISIN") == isin:
            return company
    return None

def search_companies(query: str, limit: int = 10) -> list[dict]:
    companies = load_companies()
    if not query:
        return []
    q = query.lower()
    results = [
        c for c in companies
        if q in str(c.get("name", c.get("companyName", ""))).lower()
        or q in str(c.get("isin", c.get("ISIN", ""))).lower()
    ]
    return results[:limit]
