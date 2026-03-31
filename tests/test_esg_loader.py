from data.esg_loader import load_companies, get_company_by_isin, search_companies

def test_load_companies_returns_list():
    companies = load_companies()
    assert isinstance(companies, list)
    assert len(companies) > 1000

def test_get_company_by_isin_found():
    # Apple's ISIN — adjust to one that exists in the dataset if needed
    companies = load_companies()
    if companies:
        first = companies[0]
        isin = first.get("isin") or first.get("ISIN") or ""
        if isin:
            company = get_company_by_isin(isin)
            assert company is not None

def test_get_company_by_isin_not_found():
    company = get_company_by_isin("XX0000000000")
    assert company is None

def test_search_companies():
    results = search_companies("Apple", limit=5)
    assert len(results) <= 5

def test_search_companies_empty_query():
    results = search_companies("", limit=5)
    assert isinstance(results, list)
