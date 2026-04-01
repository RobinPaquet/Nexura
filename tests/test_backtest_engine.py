import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from datetime import date


def _make_fake_prices(tickers: list, n_days: int = 400) -> pd.DataFrame:
    """Generate synthetic daily prices for testing."""
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_days, freq="B")
    np.random.seed(42)
    data = {}
    for t in tickers:
        returns = np.random.normal(0.0003, 0.015, n_days)
        data[t] = 100 * np.cumprod(1 + returns)
    return pd.DataFrame(data, index=dates)


FAKE_ESG_COMPANIES = [
    {"ticker": "AAPL", "name": "Apple", "isin": "US0378331005", "totalScore": 75.0, "sector": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft", "isin": "US5949181045", "totalScore": 82.0, "sector": "Technology"},
    {"ticker": "XOM", "name": "ExxonMobil", "isin": "US30231G1022", "totalScore": 30.0, "sector": "Energy/oil"},
    {"ticker": "JPM", "name": "JPMorgan", "isin": "US46625H1005", "totalScore": 60.0, "sector": "Finance"},
    {"ticker": "JNJ", "name": "J&J", "isin": "US4781601046", "totalScore": 70.0, "sector": "Healthcare"},
]


def test_filter_companies_by_esg_min():
    from services.backtest_engine import filter_companies
    result = filter_companies(
        FAKE_ESG_COMPANIES,
        universe_tickers=["AAPL", "MSFT", "XOM", "JPM", "JNJ"],
        esg_min=65.0,
        sectors_exclude=[],
    )
    tickers = [r["ticker"] for r in result]
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "XOM" not in tickers  # score 30 < 65
    assert "JPM" not in tickers  # score 60 < 65


def test_filter_companies_excludes_sectors():
    from services.backtest_engine import filter_companies
    result = filter_companies(
        FAKE_ESG_COMPANIES,
        universe_tickers=["AAPL", "MSFT", "XOM", "JPM", "JNJ"],
        esg_min=0.0,
        sectors_exclude=["oil", "energy"],
    )
    tickers = [r["ticker"] for r in result]
    assert "XOM" not in tickers
    assert "AAPL" in tickers


def test_compute_weights_proportional_to_score():
    from services.backtest_engine import compute_weights
    companies = [
        {"ticker": "A", "composite_score": 80.0},
        {"ticker": "B", "composite_score": 40.0},
    ]
    weights = compute_weights(companies, esg_weighted=True)
    assert abs(weights["A"] - 80/120) < 0.001
    assert abs(weights["B"] - 40/120) < 0.001
    assert abs(sum(weights.values()) - 1.0) < 0.001


def test_compute_weights_equal_when_not_esg_weighted():
    from services.backtest_engine import compute_weights
    companies = [{"ticker": "A", "composite_score": 80}, {"ticker": "B", "composite_score": 40}]
    weights = compute_weights(companies, esg_weighted=False)
    assert abs(weights["A"] - 0.5) < 0.001
    assert abs(weights["B"] - 0.5) < 0.001


def test_run_backtest_returns_expected_structure():
    from services.backtest_engine import run_backtest

    all_tickers = ["AAPL", "MSFT", "XOM", "JPM", "JNJ", "SPY"]
    fake_prices = _make_fake_prices(all_tickers, n_days=600)

    with patch("services.backtest_engine.yf.download", return_value=fake_prices), \
         patch("services.backtest_engine.load_companies", return_value=FAKE_ESG_COMPANIES), \
         patch("services.backtest_engine.load_universe", return_value=["AAPL", "MSFT", "XOM", "JPM", "JNJ"]):

        result = run_backtest({
            "universe": "sp500",
            "years": 1,
            "esg_min": 0.0,
            "sectors_exclude": [],
            "esg_weighted": True,
            "esg_momentum": False,
        })

    assert "summary" in result
    assert "performance" in result
    assert "risk" in result
    assert "attribution" in result
    assert "trades" in result
    assert "cagr" in result["summary"]
    assert "sharpe" in result["summary"]
    assert len(result["performance"]["dates"]) > 0
    assert len(result["performance"]["portfolio"]) == len(result["performance"]["dates"])
