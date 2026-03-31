import json
import os
from typing import Optional
from functools import lru_cache

ESG_DATA_PATH = os.getenv(
    "ESG_DATA_PATH",
    "/Users/robin/Desktop/Weefinnn/weefin-esg-search/Dossier_Weefin_Cours_M1/weefin-esg-search 2/public/companies.json"
)

@lru_cache(maxsize=1)
def load_companies() -> list[dict]:
    with open(ESG_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

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
