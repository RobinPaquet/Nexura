import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


FAKE_BACKTEST_RESULT = {
    "params": {},
    "summary": {"cagr": 0.12, "sharpe": 1.3, "max_drawdown": -0.15, "alpha": 0.02, "bench_cagr": 0.10},
    "performance": {"dates": ["2024-01-01"], "portfolio": [1.0], "benchmark": [1.0]},
    "risk": {"cagr": 0.12, "bench_cagr": 0.10, "volatility": 0.14, "sharpe": 1.3,
             "sortino": 1.8, "calmar": 0.8, "max_drawdown": -0.15, "drawdown_duration_days": 45,
             "beta": 0.9, "alpha": 0.02, "rolling_sharpe": {"dates": [], "values": []}},
    "attribution": {"top_contributors": [], "bottom_contributors": [],
                    "sector_weights": {}, "esg_distribution": {"labels": [], "counts": []},
                    "total_holdings": 5},
    "trades": [],
}


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)


def test_get_universes(client):
    response = client.get("/backtest/universes")
    assert response.status_code == 200
    data = response.json()
    assert "universes" in data
    assert any(u["id"] == "sp500" for u in data["universes"])
    assert any(u["id"] == "stoxx600" for u in data["universes"])


def test_run_backtest_success(client):
    with patch("routers.backtest.run_backtest", return_value=FAKE_BACKTEST_RESULT):
        response = client.post("/backtest/run", json={
            "universe": "sp500",
            "years": 1,
            "esg_min": 50.0,
            "sectors_exclude": [],
            "esg_weighted": True,
            "esg_momentum": False,
        })
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert data["summary"]["cagr"] == 0.12


def test_run_backtest_invalid_params(client):
    response = client.post("/backtest/run", json={
        "universe": "invalid_universe",
        "years": 1,
        "esg_min": 50.0,
        "sectors_exclude": [],
        "esg_weighted": True,
        "esg_momentum": False,
    })
    assert response.status_code == 422  # validation error


def test_run_backtest_engine_error_returns_400(client):
    with patch("routers.backtest.run_backtest", side_effect=ValueError("No companies match")):
        response = client.post("/backtest/run", json={
            "universe": "sp500",
            "years": 1,
            "esg_min": 99.0,
            "sectors_exclude": ["oil", "gas", "coal", "defense", "tobacco"],
            "esg_weighted": True,
            "esg_momentum": False,
        })
    assert response.status_code == 400
    assert "No companies match" in response.json()["detail"]
