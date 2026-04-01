import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock
from main import app
from models.watchlist import get_db
from models.scanner import ScannerAlert, ScannerConfig
from datetime import datetime, timezone


def make_mock_db(alerts=None, config=None):
    db = MagicMock()

    def query_side_effect(model):
        m = MagicMock()
        if model is ScannerAlert:
            m.order_by.return_value.limit.return_value.all.return_value = alerts or []
        elif model is ScannerConfig:
            m.filter.return_value.first.return_value = config
        return m

    db.query.side_effect = query_side_effect
    return db


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_alerts_empty():
    mock_db = make_mock_db(alerts=[])
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/scanner/alerts")
    assert r.status_code == 200
    assert r.json() == {"alerts": [], "count": 0}


@pytest.mark.asyncio
async def test_get_alerts_returns_list():
    alert = MagicMock(spec=ScannerAlert)
    alert.id = 1
    alert.isin = "FR0000131104"
    alert.company = "BNP Paribas"
    alert.type = "news"
    alert.sentiment = "negative"
    alert.headline = "BNP faces greenwashing lawsuit"
    alert.source_url = "https://example.com"
    alert.score = -0.8
    alert.created_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

    mock_db = make_mock_db(alerts=[alert])
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/scanner/alerts")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["alerts"][0]["isin"] == "FR0000131104"


@pytest.mark.asyncio
async def test_get_config_no_config_returns_defaults():
    mock_db = make_mock_db(config=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/scanner/config")
    assert r.status_code == 200
    body = r.json()
    assert body["esg_min"] == 0.0
    assert body["sectors_exclude"] == []


@pytest.mark.asyncio
async def test_save_config_returns_ok():
    mock_db = make_mock_db(config=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/scanner/config", json={
            "esg_min": 60.0,
            "sectors_exclude": ["oil", "coal"],
            "countries": [],
            "coverage_min": 0.5,
        })
    assert r.status_code == 200
    assert r.json()["status"] == "saved"
