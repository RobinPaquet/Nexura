import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_quote_endpoint_structure():
    mock_quote = {
        "symbol": "AAPL",
        "price": 182.50,
        "change": 2.10,
        "change_pct": 1.16,
        "volume": 52000000,
        "market_cap": 2800000000000,
        "delayed": True
    }
    with patch("routers.terminal.get_quote", return_value=mock_quote):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/terminal/quote/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert "price" in data
    assert "change_pct" in data
    assert "delayed" in data

@pytest.mark.asyncio
async def test_quote_not_found():
    with patch("routers.terminal.get_quote", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/terminal/quote/XXXXXXX")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_search_endpoint():
    mock_results = [{"isin": "US0378331005", "name": "Apple Inc.", "nexuraScore": 74}]
    with patch("routers.terminal.search_companies", return_value=mock_results):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/terminal/search?q=Apple&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data

@pytest.mark.asyncio
async def test_company_endpoint_combines_esg_and_finance():
    mock_esg = {"isin": "US0378331005", "name": "Apple Inc.", "ticker": "AAPL", "nexuraScore": 74}
    mock_finance = {"symbol": "AAPL", "price": 182.50, "change": 2.10, "change_pct": 1.16, "volume": 0, "market_cap": None, "delayed": True}
    with patch("routers.terminal.get_company_by_isin", return_value=mock_esg), \
         patch("routers.terminal.get_quote", return_value=mock_finance):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/terminal/company/US0378331005")
    assert response.status_code == 200
    data = response.json()
    assert "esg" in data
    assert "finance" in data
    assert data["isin"] == "US0378331005"

@pytest.mark.asyncio
async def test_company_not_found():
    with patch("routers.terminal.get_company_by_isin", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/terminal/company/XX0000000000")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_ohlcv_endpoint():
    mock_bars = [{"t": 1704067200000, "o": 185.0, "h": 186.0, "l": 184.0, "c": 185.5, "v": 50000000}]
    with patch("routers.terminal.get_ohlcv", return_value=mock_bars):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/terminal/ohlcv/AAPL?from_date=2024-01-01&to_date=2024-12-31")
    assert response.status_code == 200
    data = response.json()
    assert "bars" in data
    assert len(data["bars"]) == 1
    assert data["bars"][0]["c"] == 185.5
