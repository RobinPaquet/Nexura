import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from main import app

def make_mock_db(existing=None):
    db = MagicMock()
    db.query.return_value.order_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.first.return_value = existing
    return db

@pytest.mark.asyncio
async def test_get_watchlist_empty():
    mock_db = make_mock_db()
    with patch("routers.watchlist.get_db", return_value=iter([mock_db])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/watchlist")
    assert r.status_code == 200
    assert r.json() == []

@pytest.mark.asyncio
async def test_add_to_watchlist():
    mock_db = make_mock_db(existing=None)
    with patch("routers.watchlist.get_db", return_value=iter([mock_db])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/watchlist", json={"isin": "NL0010273215", "name": "ASML", "ticker": "ASML"})
    assert r.status_code == 201
    assert r.json()["status"] == "added"

@pytest.mark.asyncio
async def test_add_duplicate_returns_409():
    from models.watchlist import WatchlistItem
    existing = MagicMock(spec=WatchlistItem)
    mock_db = make_mock_db(existing=existing)
    with patch("routers.watchlist.get_db", return_value=iter([mock_db])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/watchlist", json={"isin": "NL0010273215", "name": "ASML"})
    assert r.status_code == 409

@pytest.mark.asyncio
async def test_delete_not_found_returns_404():
    mock_db = make_mock_db(existing=None)
    with patch("routers.watchlist.get_db", return_value=iter([mock_db])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.delete("/watchlist/XX0000000000")
    assert r.status_code == 404
