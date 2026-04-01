# Backtest Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a professional ESG backtest engine — vectorized, quarterly rebalancing, transaction costs, full analytics (Performance / Risk / Attribution / Trades) — exposed via FastAPI and visualized in the Weefin Terminal.

**Architecture:** Vectorized pandas engine in `services/backtest_engine.py` doing batch yfinance downloads + ESG filtering + quarterly portfolio simulation with 0.1% transaction costs. Results served by `routers/backtest.py` (POST /backtest/run). Frontend page `/backtest` with 4-tab results layout using recharts.

**Tech Stack:** Python (pandas, numpy, scipy), yfinance (already installed), FastAPI, Next.js 14, recharts, TypeScript, Tailwind CSS.

---

## Context

**Backend repo:** `/Users/robin/Desktop/Weefinnn/weefin-api/`  
**Frontend repo:** `/Users/robin/Desktop/Weefinnn/weefin-terminal/`  
**ESG data:** `data/esg_loader.py` → `load_companies()` → list of dicts with fields: `ticker`/`symbol`, `totalScore`/`score`, `sector`/`industry`, `name`/`companyName`, `isin`/`ISIN`  
**Existing market data:** `services/market_data.py` uses yfinance  
**DB pattern:** SQLAlchemy, `models/watchlist.py` as reference  
**Test pattern:** `tests/conftest.py` sets `DATABASE_URL=sqlite:///./test.db`; use `dependency_overrides` for DB, `unittest.mock.patch` for external calls  
**Run tests:** `.venv/bin/pytest tests/ -v`  
**Run server:** `.venv/bin/uvicorn main:app --reload --port 8000`

---

### Task 1: Add scipy dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add scipy to requirements.txt**

Open `requirements.txt` and add after `anthropic==0.31.0`:
```
scipy==1.13.1
recharts is frontend — added in Task 8
```

Full requirements.txt should be:
```
# Requires Python 3.11+
fastapi==0.111.0
uvicorn[standard]==0.30.1
httpx==0.27.0
yfinance==0.2.40
pandas==2.2.2
python-dotenv==1.0.1
python-multipart==0.0.9
apscheduler==3.10.4
psycopg2-binary==2.9.9
sqlalchemy==2.0.30
pytest==8.2.2
pytest-asyncio==0.23.7
anyio==4.4.0
anthropic==0.31.0
scipy==1.13.1
```

**Step 2: Install**

```bash
.venv/bin/pip install scipy==1.13.1 -q
```

Expected: installs successfully.

**Step 3: Verify import**

```bash
.venv/bin/python -c "import scipy; print(scipy.__version__)"
```

Expected: `1.13.1`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add scipy dependency for backtest metrics"
```

---

### Task 2: Create universe data files

**Files:**
- Create: `data/sp500_tickers.json`
- Create: `data/stoxx600_tickers.json`
- Create: `data/universe_loader.py`
- Create: `tests/test_universe_loader.py`

**Step 1: Write the failing test**

Create `tests/test_universe_loader.py`:
```python
import pytest
from data.universe_loader import load_universe, UNIVERSES


def test_load_sp500_returns_list():
    tickers = load_universe("sp500")
    assert isinstance(tickers, list)
    assert len(tickers) > 10
    assert all(isinstance(t, str) for t in tickers)


def test_load_stoxx600_returns_list():
    tickers = load_universe("stoxx600")
    assert isinstance(tickers, list)
    assert len(tickers) > 10


def test_load_unknown_universe_raises():
    with pytest.raises(ValueError, match="Unknown universe"):
        load_universe("nasdaq")


def test_universes_constant_has_both():
    assert "sp500" in UNIVERSES
    assert "stoxx600" in UNIVERSES
```

**Step 2: Run to verify it fails**

```bash
.venv/bin/pytest tests/test_universe_loader.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'data.universe_loader'`

**Step 3: Create `data/sp500_tickers.json`**

```json
[
  "AAPL","MSFT","NVDA","AMZN","GOOGL","GOOG","META","BRK-B","TSLA","LLY",
  "AVGO","JPM","UNH","XOM","V","COST","MA","HD","PG","MRK",
  "JNJ","ABBV","CVX","BAC","NFLX","CRM","WMT","KO","PEP","TMO",
  "ACN","AMD","CSCO","MCD","ADBE","ABT","LIN","GE","NOW","QCOM",
  "IBM","TXN","CAT","INTU","AMGN","ISRG","GS","BKNG","SPGI","AXP",
  "RTX","BLK","DE","VRTX","SYK","MDLZ","ADI","GILD","PLD","CI",
  "MMC","ZTS","SCHW","CB","MO","SO","DUK","AON","ICE","REGN",
  "CME","BSX","BDX","EOG","SLB","NOC","ITW","WM","FCX","APD",
  "ECL","FDX","MSI","NSC","ETN","EMR","HCA","MCO","ORLY","AIG",
  "TGT","PH","CTAS","KLAC","LRCX","PANW","SNPS","CDNS","MCHP","ANET"
]
```

**Step 4: Create `data/stoxx600_tickers.json`**

```json
[
  "ASML.AS","MC.PA","SAP.DE","ROG.SW","NESN.SW","RMS.PA","OR.PA","AIR.PA",
  "AZN.L","HSBA.L","SHEL.L","SIE.DE","ALV.DE","DTE.DE","MBG.DE","BMW.DE",
  "VOW3.DE","IFX.DE","ADS.DE","BNP.PA","SAN.PA","CS.PA","TTE.PA","ENEL.MI",
  "ENI.MI","ISP.MI","UCG.MI","ERICB.ST","VOLV-B.ST","NDA-SE.ST","SWED-A.ST",
  "DANSKE.CO","ORSTED.CO","MAERSK-B.CO","COLOPLAST-B.CO","ASSA-B.ST",
  "INVE-B.ST","EQT.ST","ABB.ST","UBS.SW","ZURN.SW","CSGN.SW","SGSN.SW",
  "NOVN.SW","ALC.SW","LONN.SW","BAER.SW","GIVN.SW","SIKA.SW","PGHN.SW",
  "RIO.L","BP.L","GSK.L","ULVR.L","REL.L","LSEG.L","EXPN.L","NXT.L",
  "BA.L","LLOY.L","BARC.L","NWG.L","PRU.L","STAN.L","LGEN.L","ADM.L",
  "AAL.L","BT-A.L","VOD.L","TSCO.L","DGE.L","RKT.L","CPG.L","IMB.L",
  "WEIR.L","RR.L","MGGT.L","BDEV.L","SBRY.L","MKS.L","JD.L","KGF.L",
  "FLTR.L","OCDO.L","AUTO.L","III.L","SDR.L","HLMA.L","DPLM.L","SMDS.L"
]
```

**Step 5: Create `data/universe_loader.py`**

```python
import json
import os
from functools import lru_cache

UNIVERSES = {
    "sp500": {
        "file": "sp500_tickers.json",
        "benchmark": "SPY",
        "label": "S&P 500",
    },
    "stoxx600": {
        "file": "stoxx600_tickers.json",
        "benchmark": "EXW1.DE",
        "label": "STOXX 600",
    },
}

_DATA_DIR = os.path.dirname(__file__)


@lru_cache(maxsize=None)
def load_universe(name: str) -> list:
    if name not in UNIVERSES:
        raise ValueError(f"Unknown universe '{name}'. Available: {list(UNIVERSES.keys())}")
    path = os.path.join(_DATA_DIR, UNIVERSES[name]["file"])
    with open(path, "r") as f:
        return json.load(f)


def get_benchmark_ticker(universe: str) -> str:
    return UNIVERSES[universe]["benchmark"]
```

**Step 6: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_universe_loader.py -v
```

Expected: 4 PASSED

**Step 7: Commit**

```bash
git add data/sp500_tickers.json data/stoxx600_tickers.json data/universe_loader.py tests/test_universe_loader.py
git commit -m "feat: add S&P500/STOXX600 universe data files and loader"
```

---

### Task 3: Backtest engine — price download + portfolio simulation

**Files:**
- Create: `services/backtest_engine.py`
- Create: `tests/test_backtest_engine.py`

**Step 1: Write the failing tests**

Create `tests/test_backtest_engine.py`:
```python
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
```

**Step 2: Run to verify it fails**

```bash
.venv/bin/pytest tests/test_backtest_engine.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.backtest_engine'`

**Step 3: Create `services/backtest_engine.py`**

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from data.esg_loader import load_companies
from data.universe_loader import load_universe, get_benchmark_ticker

TRANSACTION_COST = 0.001  # 0.1% per trade
MAX_HOLDINGS = 50
RISK_FREE_RATE = 0.02


def run_backtest(params: dict) -> dict:
    universe_name = params["universe"]
    years = int(params.get("years", 5))
    esg_min = float(params.get("esg_min", 0))
    sectors_exclude = [s.lower() for s in params.get("sectors_exclude", [])]
    esg_weighted = bool(params.get("esg_weighted", True))
    esg_momentum = bool(params.get("esg_momentum", False))

    universe_tickers = load_universe(universe_name)
    benchmark_ticker = get_benchmark_ticker(universe_name)
    companies = load_companies()

    # Filter companies by universe + ESG criteria
    filtered = filter_companies(companies, universe_tickers, esg_min, sectors_exclude)
    if not filtered:
        raise ValueError("No companies match the ESG filters. Reduce esg_min or sector exclusions.")

    # Add composite score
    for c in filtered:
        base_score = float(c.get("totalScore") or c.get("score") or 50)
        if esg_momentum:
            # Synthetic momentum: shuffle rank slightly with seeded noise per ticker
            import hashlib
            seed = int(hashlib.md5(c["ticker"].encode()).hexdigest()[:8], 16) % 100
            momentum_rank = seed / 100.0
        else:
            momentum_rank = 0.5
        c["composite_score"] = 0.7 * base_score + 0.3 * (momentum_rank * 100)

    # Sort by composite score, take top MAX_HOLDINGS
    filtered.sort(key=lambda x: x["composite_score"], reverse=True)
    filtered = filtered[:MAX_HOLDINGS]

    strategy_tickers = [c["ticker"] for c in filtered]
    all_tickers = strategy_tickers + [benchmark_ticker]

    # Date range
    end_date = datetime.today()
    start_date = end_date - timedelta(days=365 * years + 30)  # extra 30 days buffer

    # Batch download prices
    raw = yf.download(
        all_tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )

    # yfinance returns MultiIndex if multiple tickers, Series if single
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]].rename(columns={"Close": all_tickers[0]})

    # Drop tickers with >50% missing data
    prices = prices.dropna(axis=1, thresh=int(len(prices) * 0.5))
    available_strategy = [t for t in strategy_tickers if t in prices.columns]
    filtered = [c for c in filtered if c["ticker"] in available_strategy]

    if not filtered:
        raise ValueError("No price data found for filtered companies.")

    # Build quarterly rebalancing schedule
    rebal_dates = pd.date_range(start=start_date, end=end_date, freq="QS")

    equity_curve = _simulate_portfolio(prices, filtered, benchmark_ticker, rebal_dates, esg_weighted)

    port_series = pd.Series(
        equity_curve["portfolio_values"], index=pd.to_datetime(equity_curve["dates"])
    )
    bench_series = pd.Series(
        equity_curve["benchmark_values"], index=pd.to_datetime(equity_curve["dates"])
    )

    port_returns = port_series.pct_change().dropna()
    bench_returns = bench_series.pct_change().dropna()

    # Align
    common_idx = port_returns.index.intersection(bench_returns.index)
    port_returns = port_returns.loc[common_idx]
    bench_returns = bench_returns.loc[common_idx]

    metrics = compute_metrics(port_returns, bench_returns)
    attribution = compute_attribution(prices, filtered, rebal_dates)

    return {
        "params": params,
        "summary": {
            "cagr": metrics["cagr"],
            "sharpe": metrics["sharpe"],
            "max_drawdown": metrics["max_drawdown"],
            "alpha": metrics["alpha"],
            "bench_cagr": metrics["bench_cagr"],
        },
        "performance": {
            "dates": [str(d) for d in port_series.index],
            "portfolio": [round(v, 4) for v in port_series.values],
            "benchmark": [round(v, 4) for v in bench_series.values],
        },
        "risk": metrics,
        "attribution": attribution,
        "trades": equity_curve["trades"],
    }


def filter_companies(
    companies: list,
    universe_tickers: list,
    esg_min: float,
    sectors_exclude: list,
) -> list:
    universe_set = {t.upper() for t in universe_tickers}
    result = []
    for c in companies:
        ticker = str(c.get("ticker") or c.get("symbol") or "").strip()
        if not ticker or ticker.upper() not in universe_set:
            continue
        score = float(c.get("totalScore") or c.get("score") or 0)
        if score < esg_min:
            continue
        sector = str(c.get("sector") or c.get("industry") or "").lower()
        if any(excl in sector for excl in sectors_exclude):
            continue
        result.append({**c, "ticker": ticker, "score": score})
    return result


def compute_weights(companies: list, esg_weighted: bool) -> dict:
    if not companies:
        return {}
    if esg_weighted:
        total = sum(c["composite_score"] for c in companies)
        if total == 0:
            return {c["ticker"]: 1 / len(companies) for c in companies}
        return {c["ticker"]: c["composite_score"] / total for c in companies}
    else:
        n = len(companies)
        return {c["ticker"]: 1 / n for c in companies}


def _simulate_portfolio(
    prices: pd.DataFrame,
    filtered: list,
    benchmark_ticker: str,
    rebal_dates: pd.DatetimeIndex,
    esg_weighted: bool,
) -> dict:
    portfolio_value = 1.0
    benchmark_value = 1.0
    all_dates = []
    port_values = []
    bench_values = []
    trades_log = []
    prev_weights: dict = {}

    for i in range(len(rebal_dates) - 1):
        period_start = rebal_dates[i]
        period_end = rebal_dates[i + 1]

        # Available tickers in this period
        period_prices = prices.loc[period_start:period_end]
        available = [
            c["ticker"] for c in filtered
            if c["ticker"] in prices.columns
            and not period_prices[c["ticker"]].isna().all()
        ]
        if not available:
            continue

        period_filtered = [c for c in filtered if c["ticker"] in available]
        weights = compute_weights(period_filtered, esg_weighted)

        # Transaction cost
        all_tickers_period = set(list(weights.keys()) + list(prev_weights.keys()))
        turnover = sum(
            abs(weights.get(t, 0) - prev_weights.get(t, 0))
            for t in all_tickers_period
        )
        cost = turnover * TRANSACTION_COST

        # Portfolio daily returns for this period
        period_returns = period_prices[available].pct_change().dropna()
        if period_returns.empty:
            continue

        weight_array = np.array([weights.get(t, 0) for t in available])
        port_daily = period_returns[available].values @ weight_array
        port_segment = (1 + port_daily).cumprod() * (1 - cost)

        # Benchmark daily returns
        if benchmark_ticker in prices.columns:
            bench_daily = period_prices[benchmark_ticker].pct_change().dropna()
            bench_segment = (1 + bench_daily).cumprod()
        else:
            bench_segment = pd.Series(np.ones(len(port_segment)), index=period_returns.index)

        # Normalize benchmark segment to same length
        common = period_returns.index
        bench_segment = bench_segment.reindex(common).ffill().bfill()

        dates_in_period = [str(d.date()) for d in common]
        port_vals_in_period = [float(v) * portfolio_value for v in port_segment]
        bench_vals_in_period = [float(v) * benchmark_value for v in bench_segment]

        all_dates.extend(dates_in_period)
        port_values.extend(port_vals_in_period)
        bench_values.extend(bench_vals_in_period)

        portfolio_value = port_vals_in_period[-1] if port_vals_in_period else portfolio_value
        benchmark_value = bench_vals_in_period[-1] if bench_vals_in_period else benchmark_value

        trades_log.append({
            "date": str(period_start.date()),
            "holdings": len(available),
            "turnover": round(turnover, 4),
            "cost_pct": round(cost * 100, 4),
            "top_holdings": [
                {"ticker": t, "weight": round(weights[t] * 100, 2)}
                for t in sorted(weights, key=weights.get, reverse=True)[:5]
            ],
        })

        prev_weights = weights

    return {
        "dates": all_dates,
        "portfolio_values": port_values,
        "benchmark_values": bench_values,
        "trades": trades_log,
    }


def compute_metrics(port_returns: pd.Series, bench_returns: pd.Series) -> dict:
    td = 252  # trading days

    if len(port_returns) < 2:
        return _empty_metrics()

    cagr = float((1 + port_returns).prod() ** (td / len(port_returns)) - 1)
    bench_cagr = float((1 + bench_returns).prod() ** (td / len(bench_returns)) - 1)

    vol = float(port_returns.std() * np.sqrt(td))

    sharpe = (cagr - RISK_FREE_RATE) / vol if vol > 0 else 0.0

    downside = port_returns[port_returns < 0].std() * np.sqrt(td)
    sortino = float((cagr - RISK_FREE_RATE) / downside) if downside > 0 else 0.0

    equity = (1 + port_returns).cumprod()
    drawdown = (equity / equity.cummax()) - 1
    max_dd = float(drawdown.min())

    dd_end = drawdown.idxmin()
    dd_start = equity.loc[:dd_end].idxmax()
    dd_duration = max((dd_end - dd_start).days, 0)

    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0

    cov_matrix = np.cov(port_returns.values, bench_returns.values)
    beta = float(cov_matrix[0, 1] / cov_matrix[1, 1]) if cov_matrix[1, 1] > 0 else 1.0
    alpha = float(cagr - (RISK_FREE_RATE + beta * (bench_cagr - RISK_FREE_RATE)))

    rolling_window = min(252, len(port_returns) // 2)
    rolling = port_returns.rolling(rolling_window)
    rs = (rolling.mean() * td - RISK_FREE_RATE) / (rolling.std() * np.sqrt(td))
    rs_clean = rs.dropna()

    return {
        "cagr": round(cagr, 4),
        "bench_cagr": round(bench_cagr, 4),
        "volatility": round(vol, 4),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "calmar": round(calmar, 3),
        "max_drawdown": round(max_dd, 4),
        "drawdown_duration_days": dd_duration,
        "beta": round(beta, 3),
        "alpha": round(alpha, 4),
        "rolling_sharpe": {
            "dates": [str(d.date()) for d in rs_clean.index],
            "values": [round(float(v), 3) for v in rs_clean.values],
        },
    }


def compute_attribution(
    prices: pd.DataFrame, filtered: list, rebal_dates: pd.DatetimeIndex
) -> dict:
    # Per-ticker contribution over full period
    contributions = []
    for c in filtered:
        t = c["ticker"]
        if t not in prices.columns:
            continue
        series = prices[t].dropna()
        if len(series) < 2:
            continue
        total_return = float(series.iloc[-1] / series.iloc[0] - 1)
        weight = c.get("composite_score", 50) / sum(
            x.get("composite_score", 50) for x in filtered
        )
        contributions.append({
            "ticker": t,
            "name": str(c.get("name") or c.get("companyName") or t),
            "contribution": round(total_return * weight, 4),
            "return": round(total_return, 4),
            "weight": round(weight, 4),
        })

    contributions.sort(key=lambda x: x["contribution"], reverse=True)
    top_contributors = contributions[:10]
    bottom_contributors = sorted(contributions, key=lambda x: x["contribution"])[:5]

    # Sector weights
    sector_weights: dict = {}
    total_score = sum(c.get("composite_score", 50) for c in filtered)
    for c in filtered:
        sector = str(c.get("sector") or c.get("industry") or "Other")
        weight = c.get("composite_score", 50) / total_score if total_score > 0 else 0
        sector_weights[sector] = round(sector_weights.get(sector, 0) + weight, 4)

    # ESG score distribution
    scores = [float(c.get("score") or c.get("totalScore") or 0) for c in filtered]
    buckets = [0, 20, 40, 60, 80, 100]
    counts = [0] * (len(buckets) - 1)
    for s in scores:
        for j in range(len(buckets) - 1):
            if buckets[j] <= s < buckets[j + 1]:
                counts[j] += 1
                break
        else:
            counts[-1] += 1  # 100

    return {
        "top_contributors": top_contributors,
        "bottom_contributors": bottom_contributors,
        "sector_weights": sector_weights,
        "esg_distribution": {
            "labels": [f"{buckets[j]}-{buckets[j+1]}" for j in range(len(buckets)-1)],
            "counts": counts,
        },
        "total_holdings": len(filtered),
    }


def _empty_metrics() -> dict:
    return {
        "cagr": 0.0, "bench_cagr": 0.0, "volatility": 0.0,
        "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0,
        "max_drawdown": 0.0, "drawdown_duration_days": 0,
        "beta": 1.0, "alpha": 0.0,
        "rolling_sharpe": {"dates": [], "values": []},
    }
```

**Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_backtest_engine.py -v
```

Expected: 5 PASSED

**Step 5: Commit**

```bash
git add services/backtest_engine.py tests/test_backtest_engine.py
git commit -m "feat: add vectorized backtest engine with ESG filtering and metrics"
```

---

### Task 4: Backtest router

**Files:**
- Create: `routers/backtest.py`
- Create: `tests/test_backtest_router.py`

**Step 1: Write the failing test**

Create `tests/test_backtest_router.py`:
```python
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
```

Note: the `client` fixture is already defined in `tests/conftest.py` if the test for the router follows the same pattern as `tests/test_scanner_router.py`. Check that file first — it defines a `client` fixture using `TestClient(app)`. If `conftest.py` doesn't have it, add it:

Check `tests/test_scanner_router.py` for the client fixture pattern. It likely looks like:
```python
@pytest.fixture
def client():
    from main import app
    return TestClient(app)
```

Add this to `tests/conftest.py` if not present.

**Step 2: Run to verify it fails**

```bash
.venv/bin/pytest tests/test_backtest_router.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'routers.backtest'`

**Step 3: Create `routers/backtest.py`**

```python
from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.backtest_engine import run_backtest
from data.universe_loader import UNIVERSES

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestParams(BaseModel):
    universe: Literal["sp500", "stoxx600"]
    years: int = Field(default=5, ge=1, le=10)
    esg_min: float = Field(default=0.0, ge=0.0, le=100.0)
    sectors_exclude: list[str] = Field(default_factory=list)
    esg_weighted: bool = True
    esg_momentum: bool = False


@router.get("/universes")
def get_universes():
    return {
        "universes": [
            {"id": key, "label": val["label"], "benchmark": val["benchmark"]}
            for key, val in UNIVERSES.items()
        ]
    }


@router.post("/run")
def run(params: BacktestParams):
    try:
        result = run_backtest(params.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")
```

**Step 4: Check conftest.py for client fixture**

Read `tests/test_scanner_router.py` to see how it defines the `client` fixture. If it defines it locally, add a shared one to `tests/conftest.py`:

```python
# Add to tests/conftest.py
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)
```

**Step 5: Wire up router in `main.py`**

Add after the scanner router lines:
```python
from routers.backtest import router as backtest_router
app.include_router(backtest_router)
```

**Step 6: Run tests**

```bash
.venv/bin/pytest tests/test_backtest_router.py -v
```

Expected: 4 PASSED

**Step 7: Run full suite**

```bash
.venv/bin/pytest tests/ -v
```

Expected: all tests pass (was 32, now ~40).

**Step 8: Commit**

```bash
git add routers/backtest.py tests/test_backtest_router.py main.py tests/conftest.py
git commit -m "feat: add backtest router (GET /backtest/universes, POST /backtest/run)"
```

---

### Task 5: Frontend — install recharts + add API function

**Files:**
- Modify: `package.json` (via npm install)
- Modify: `src/lib/api.ts`

**Step 1: Install recharts**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-terminal
npm install recharts
```

Expected: recharts added to package.json dependencies.

**Step 2: Add backtest API functions to `src/lib/api.ts`**

Add at the end of the file:

```typescript
export interface BacktestParams {
  universe: "sp500" | "stoxx600";
  years: number;
  esg_min: number;
  sectors_exclude: string[];
  esg_weighted: boolean;
  esg_momentum: boolean;
}

export async function runBacktest(params: BacktestParams) {
  const res = await fetch(`${API_URL}/backtest/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Backtest failed" }));
    throw new Error(err.detail || "Backtest failed");
  }
  return res.json();
}

export async function fetchBacktestUniverses() {
  const res = await fetch(`${API_URL}/backtest/universes`);
  if (!res.ok) throw new Error("Failed to fetch universes");
  return res.json();
}
```

**Step 3: Commit**

```bash
git add src/lib/api.ts package.json package-lock.json
git commit -m "feat: add backtest API functions and install recharts"
```

---

### Task 6: Frontend — BacktestConfigPanel component

**Files:**
- Create: `src/components/BacktestConfigPanel.tsx`

**Step 1: Create `src/components/BacktestConfigPanel.tsx`**

```tsx
"use client";
import { useState } from "react";
import type { BacktestParams } from "@/lib/api";

interface BacktestConfigPanelProps {
  onRun: (params: BacktestParams) => void;
  loading: boolean;
}

const SECTOR_OPTIONS = ["oil", "coal", "gas", "defense", "tobacco", "weapons"];

export default function BacktestConfigPanel({ onRun, loading }: BacktestConfigPanelProps) {
  const [universe, setUniverse] = useState<"sp500" | "stoxx600">("sp500");
  const [years, setYears] = useState(5);
  const [esgMin, setEsgMin] = useState(0);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [esgWeighted, setEsgWeighted] = useState(true);
  const [esgMomentum, setEsgMomentum] = useState(false);

  function toggleSector(s: string) {
    setExcluded((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  }

  function handleSubmit() {
    onRun({ universe, years, esg_min: esgMin, sectors_exclude: excluded, esg_weighted: esgWeighted, esg_momentum: esgMomentum });
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 flex flex-col gap-4">
      <h2 className="text-zinc-200 text-sm font-semibold uppercase tracking-wide">
        Paramètres
      </h2>

      <div>
        <label className="text-zinc-400 text-xs mb-1 block">Univers</label>
        <select
          value={universe}
          onChange={(e) => setUniverse(e.target.value as "sp500" | "stoxx600")}
          className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs rounded px-2 py-1.5"
        >
          <option value="sp500">S&P 500</option>
          <option value="stoxx600">STOXX 600</option>
        </select>
      </div>

      <div>
        <label className="text-zinc-400 text-xs mb-1 block">
          Période : <span className="text-teal-400 font-mono">{years} ans</span>
        </label>
        <input
          type="range" min={1} max={5} step={1} value={years}
          onChange={(e) => setYears(Number(e.target.value))}
          className="w-full accent-teal-500"
        />
      </div>

      <div>
        <label className="text-zinc-400 text-xs mb-1 block">
          Score ESG minimum : <span className="text-teal-400 font-mono">{esgMin}</span>
        </label>
        <input
          type="range" min={0} max={100} step={5} value={esgMin}
          onChange={(e) => setEsgMin(Number(e.target.value))}
          className="w-full accent-teal-500"
        />
      </div>

      <div>
        <label className="text-zinc-400 text-xs mb-2 block">Secteurs exclus</label>
        <div className="flex flex-wrap gap-2">
          {SECTOR_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => toggleSector(s)}
              className={`px-2 py-1 rounded text-xs border ${
                excluded.includes(s)
                  ? "bg-red-900/40 border-red-700 text-red-300"
                  : "border-zinc-700 text-zinc-500 hover:border-zinc-500"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox" checked={esgWeighted} onChange={(e) => setEsgWeighted(e.target.checked)}
            className="accent-teal-500"
          />
          <span className="text-zinc-400 text-xs">Pondération ESG</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox" checked={esgMomentum} onChange={(e) => setEsgMomentum(e.target.checked)}
            className="accent-teal-500"
          />
          <span className="text-zinc-400 text-xs">Momentum ESG</span>
        </label>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs font-medium py-2 rounded"
      >
        {loading ? "Calcul en cours…" : "Lancer le backtest"}
      </button>
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-terminal
npx tsc --noEmit
```

Expected: no errors.

**Step 3: Commit**

```bash
git add src/components/BacktestConfigPanel.tsx
git commit -m "feat: add BacktestConfigPanel component"
```

---

### Task 7: Frontend — BacktestResults component (4 tabs)

**Files:**
- Create: `src/components/BacktestResults.tsx`

This is the main results component. It requires recharts — import only what's needed.

**Step 1: Create `src/components/BacktestResults.tsx`**

```tsx
"use client";
import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, CartesianGrid,
} from "recharts";

interface BacktestResult {
  summary: { cagr: number; sharpe: number; max_drawdown: number; alpha: number; bench_cagr: number };
  performance: { dates: string[]; portfolio: number[]; benchmark: number[] };
  risk: {
    cagr: number; bench_cagr: number; volatility: number; sharpe: number; sortino: number;
    calmar: number; max_drawdown: number; drawdown_duration_days: number; beta: number; alpha: number;
    rolling_sharpe: { dates: string[]; values: number[] };
  };
  attribution: {
    top_contributors: { ticker: string; name: string; contribution: number; return: number; weight: number }[];
    bottom_contributors: { ticker: string; name: string; contribution: number }[];
    sector_weights: Record<string, number>;
    esg_distribution: { labels: string[]; counts: number[] };
    total_holdings: number;
  };
  trades: { date: string; holdings: number; turnover: number; cost_pct: number; top_holdings: { ticker: string; weight: number }[] }[];
}

interface BacktestResultsProps {
  result: BacktestResult;
}

type Tab = "performance" | "risk" | "attribution" | "trades";

function pct(v: number) { return `${(v * 100).toFixed(2)}%`; }
function fmt(v: number, decimals = 3) { return v.toFixed(decimals); }

const METRIC_ROWS = [
  { label: "CAGR Stratégie", key: "cagr", format: pct },
  { label: "CAGR Benchmark", key: "bench_cagr", format: pct },
  { label: "Volatilité annualisée", key: "volatility", format: pct },
  { label: "Sharpe ratio", key: "sharpe", format: (v: number) => fmt(v) },
  { label: "Sortino ratio", key: "sortino", format: (v: number) => fmt(v) },
  { label: "Calmar ratio", key: "calmar", format: (v: number) => fmt(v) },
  { label: "Max Drawdown", key: "max_drawdown", format: pct },
  { label: "Durée max drawdown", key: "drawdown_duration_days", format: (v: number) => `${v} jours` },
  { label: "Beta", key: "beta", format: (v: number) => fmt(v) },
  { label: "Alpha annualisé", key: "alpha", format: pct },
];

export default function BacktestResults({ result }: BacktestResultsProps) {
  const [tab, setTab] = useState<Tab>("performance");

  // Build equity curve data
  const equityData = result.performance.dates.map((d, i) => ({
    date: d,
    Stratégie: result.performance.portfolio[i],
    Benchmark: result.performance.benchmark[i],
  }));

  // Sample equity data for display (max 300 points)
  const step = Math.max(1, Math.floor(equityData.length / 300));
  const sampledEquity = equityData.filter((_, i) => i % step === 0);

  // Rolling sharpe data
  const rsData = result.risk.rolling_sharpe.dates.map((d, i) => ({
    date: d,
    "Sharpe 12M": result.risk.rolling_sharpe.values[i],
  }));
  const stepRs = Math.max(1, Math.floor(rsData.length / 200));
  const sampledRs = rsData.filter((_, i) => i % stepRs === 0);

  // Sector data for bar chart
  const sectorData = Object.entries(result.attribution.sector_weights)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([sector, weight]) => ({ sector: sector.slice(0, 20), weight: Math.round(weight * 100) }));

  // ESG distribution
  const esgDistData = result.attribution.esg_distribution.labels.map((label, i) => ({
    label,
    count: result.attribution.esg_distribution.counts[i],
  }));

  const tabs: { id: Tab; label: string }[] = [
    { id: "performance", label: "Performance" },
    { id: "risk", label: "Risk" },
    { id: "attribution", label: "Attribution" },
    { id: "trades", label: "Trades" },
  ];

  return (
    <div>
      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        {[
          { label: "CAGR", value: pct(result.summary.cagr), positive: result.summary.cagr > 0 },
          { label: "Sharpe", value: fmt(result.summary.sharpe), positive: result.summary.sharpe > 1 },
          { label: "Max DD", value: pct(result.summary.max_drawdown), positive: false },
          { label: "Alpha", value: pct(result.summary.alpha), positive: result.summary.alpha > 0 },
        ].map((m) => (
          <div key={m.label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
            <div className="text-zinc-500 text-xs mb-1">{m.label}</div>
            <div className={`text-lg font-mono font-semibold ${m.positive ? "text-teal-400" : "text-zinc-200"}`}>
              {m.value}
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-zinc-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-xs font-medium border-b-2 -mb-px transition-colors ${
              tab === t.id
                ? "border-teal-400 text-teal-400"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Performance tab */}
      {tab === "performance" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-zinc-400 text-xs uppercase tracking-wide mb-4">
            Évolution du portefeuille (base 1)
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={sampledEquity}>
              <XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false}
                interval={Math.floor(sampledEquity.length / 6)} />
              <YAxis tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: 6, fontSize: 11 }}
                labelStyle={{ color: "#a1a1aa" }}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: "#a1a1aa" }} />
              <Line type="monotone" dataKey="Stratégie" stroke="#14b8a6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Benchmark" stroke="#52525b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Risk tab */}
      {tab === "risk" && (
        <div className="flex flex-col gap-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h3 className="text-zinc-400 text-xs uppercase tracking-wide mb-3">Métriques de risque</h3>
            <div className="grid grid-cols-2 gap-x-8 gap-y-2">
              {METRIC_ROWS.map((row) => (
                <div key={row.key} className="flex justify-between items-center py-1 border-b border-zinc-800/50">
                  <span className="text-zinc-500 text-xs">{row.label}</span>
                  <span className="text-zinc-200 text-xs font-mono">
                    {row.format((result.risk as Record<string, number>)[row.key])}
                  </span>
                </div>
              ))}
            </div>
          </div>
          {sampledRs.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h3 className="text-zinc-400 text-xs uppercase tracking-wide mb-4">Rolling Sharpe (12 mois)</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={sampledRs}>
                  <XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false}
                    interval={Math.floor(sampledRs.length / 5)} />
                  <YAxis tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: 6, fontSize: 11 }}/>
                  <Line type="monotone" dataKey="Sharpe 12M" stroke="#14b8a6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Attribution tab */}
      {tab === "attribution" && (
        <div className="flex flex-col gap-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h3 className="text-zinc-400 text-xs uppercase tracking-wide mb-3">
              Top contributeurs ({result.attribution.total_holdings} titres)
            </h3>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-600 border-b border-zinc-800">
                  <th className="text-left py-1 font-normal">Ticker</th>
                  <th className="text-right py-1 font-normal">Rendement</th>
                  <th className="text-right py-1 font-normal">Poids</th>
                  <th className="text-right py-1 font-normal">Contribution</th>
                </tr>
              </thead>
              <tbody>
                {result.attribution.top_contributors.map((c) => (
                  <tr key={c.ticker} className="border-b border-zinc-800/30">
                    <td className="py-1 text-zinc-300 font-mono">{c.ticker}</td>
                    <td className={`py-1 text-right font-mono ${c.return >= 0 ? "text-teal-400" : "text-red-400"}`}>
                      {pct(c.return)}
                    </td>
                    <td className="py-1 text-right text-zinc-400 font-mono">{pct(c.weight)}</td>
                    <td className={`py-1 text-right font-mono ${c.contribution >= 0 ? "text-teal-400" : "text-red-400"}`}>
                      {pct(c.contribution)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {sectorData.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h3 className="text-zinc-400 text-xs uppercase tracking-wide mb-4">Répartition sectorielle (%)</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={sectorData} layout="vertical">
                  <XAxis type="number" tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} />
                  <YAxis type="category" dataKey="sector" tick={{ fill: "#a1a1aa", fontSize: 10 }} tickLine={false} width={120} />
                  <Tooltip contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: 6, fontSize: 11 }} />
                  <Bar dataKey="weight" fill="#14b8a6" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h3 className="text-zinc-400 text-xs uppercase tracking-wide mb-4">Distribution scores ESG</h3>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={esgDistData}>
                <XAxis dataKey="label" tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ backgroundColor: "#18181b", border: "1px solid #3f3f46", borderRadius: 6, fontSize: 11 }} />
                <Bar dataKey="count" fill="#0d9488" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Trades tab */}
      {tab === "trades" && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <h3 className="text-zinc-400 text-xs uppercase tracking-wide mb-3">
            Log des rebalancements ({result.trades.length} périodes)
          </h3>
          {result.trades.length === 0 ? (
            <p className="text-zinc-600 text-sm text-center py-8">Aucun rebalancement enregistré.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {result.trades.map((trade, i) => (
                <div key={i} className="border border-zinc-800 rounded p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-zinc-300 text-xs font-mono">{trade.date}</span>
                    <div className="flex gap-4 text-xs">
                      <span className="text-zinc-500">{trade.holdings} titres</span>
                      <span className="text-zinc-500">Turnover: <span className="text-zinc-300 font-mono">{(trade.turnover * 100).toFixed(1)}%</span></span>
                      <span className="text-zinc-500">Coût: <span className="text-red-400 font-mono">{trade.cost_pct.toFixed(3)}%</span></span>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {trade.top_holdings.map((h) => (
                      <span key={h.ticker} className="bg-zinc-800 text-zinc-400 text-xs px-2 py-0.5 rounded font-mono">
                        {h.ticker} {h.weight.toFixed(1)}%
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Check TypeScript**

```bash
npx tsc --noEmit
```

Expected: no errors.

**Step 3: Commit**

```bash
git add src/components/BacktestResults.tsx
git commit -m "feat: add BacktestResults component with 4-tab analytics layout"
```

---

### Task 8: Frontend — /backtest page + nav link

**Files:**
- Create: `src/app/backtest/page.tsx`
- Modify: `src/app/page.tsx` (add nav link)
- Modify: `src/app/scanner/page.tsx` (add nav link)

**Step 1: Create `src/app/backtest/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import Link from "next/link";
import BacktestConfigPanel from "@/components/BacktestConfigPanel";
import BacktestResults from "@/components/BacktestResults";
import { runBacktest } from "@/lib/api";
import type { BacktestParams } from "@/lib/api";

export default function BacktestPage() {
  const [result, setResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRun(params: BacktestParams) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await runBacktest(params);
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Backtest échoué.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-4">
        <Link href="/" className="text-teal-400 font-bold text-lg tracking-tight hover:text-teal-300">
          WEEFIN
        </Link>
        <span className="text-zinc-600 text-sm">TERMINAL</span>
        <nav className="flex items-center gap-4 ml-4">
          <Link href="/" className="text-zinc-500 text-sm hover:text-zinc-300">Terminal</Link>
          <Link href="/scanner" className="text-zinc-500 text-sm hover:text-zinc-300">Scanner</Link>
          <span className="text-teal-400 text-sm font-medium">Backtest</span>
        </nav>
      </header>

      <div className="p-6 max-w-6xl mx-auto">
        <h1 className="text-zinc-200 text-base font-semibold mb-4">Backtest ESG</h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-1">
            <BacktestConfigPanel onRun={handleRun} loading={loading} />
          </div>
          <div className="md:col-span-2">
            {loading && (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <div className="text-zinc-400 text-sm mb-2">Calcul en cours…</div>
                  <div className="text-zinc-600 text-xs">Téléchargement des données historiques (~10-30s)</div>
                </div>
              </div>
            )}
            {error && (
              <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400 text-sm">
                {error}
              </div>
            )}
            {!loading && !result && !error && (
              <div className="flex items-center justify-center h-64 text-zinc-600 text-sm text-center">
                <div>
                  <p className="mb-2">Configurez vos paramètres et lancez le backtest</p>
                  <p className="text-xs">Stratégie ESG sur S&P 500 ou STOXX 600 · 5 ans · Rebalancement trimestriel</p>
                </div>
              </div>
            )}
            {result && !loading && (
              <BacktestResults result={result as Parameters<typeof BacktestResults>[0]["result"]} />
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
```

**Step 2: Add Backtest nav link to `src/app/page.tsx`**

Find the nav section in `src/app/page.tsx` (around line 79-83):
```tsx
<nav className="flex items-center gap-4 ml-2">
  <span className="text-teal-400 text-sm font-medium">Terminal</span>
  <Link href="/scanner" className="text-zinc-500 text-sm hover:text-zinc-300">
    Scanner
  </Link>
</nav>
```

Replace with:
```tsx
<nav className="flex items-center gap-4 ml-2">
  <span className="text-teal-400 text-sm font-medium">Terminal</span>
  <Link href="/scanner" className="text-zinc-500 text-sm hover:text-zinc-300">
    Scanner
  </Link>
  <Link href="/backtest" className="text-zinc-500 text-sm hover:text-zinc-300">
    Backtest
  </Link>
</nav>
```

**Step 3: Add Backtest nav link to `src/app/scanner/page.tsx`**

Find the nav section (around line 62-65):
```tsx
<nav className="flex items-center gap-4 ml-4">
  <Link href="/" className="text-zinc-500 text-sm hover:text-zinc-300">
    Terminal
  </Link>
  <span className="text-teal-400 text-sm font-medium">Scanner</span>
</nav>
```

Replace with:
```tsx
<nav className="flex items-center gap-4 ml-4">
  <Link href="/" className="text-zinc-500 text-sm hover:text-zinc-300">
    Terminal
  </Link>
  <span className="text-teal-400 text-sm font-medium">Scanner</span>
  <Link href="/backtest" className="text-zinc-500 text-sm hover:text-zinc-300">
    Backtest
  </Link>
</nav>
```

**Step 4: Check TypeScript and build**

```bash
npx tsc --noEmit
```

Expected: no errors.

**Step 5: Commit**

```bash
git add src/app/backtest/page.tsx src/app/page.tsx src/app/scanner/page.tsx
git commit -m "feat: add /backtest page with config panel, results tabs, and nav links"
```

---

### Task 9: Push and deploy

**Step 1: Push backend**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-api
git push origin main
```

Expected: Railway auto-deploys.

**Step 2: Push frontend**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-terminal
git push
```

Expected: Vercel auto-deploys.

**Step 3: Verify backend**

```bash
curl https://web-production-9cd14.up.railway.app/backtest/universes
```

Expected:
```json
{"universes":[{"id":"sp500","label":"S&P 500","benchmark":"SPY"},{"id":"stoxx600","label":"STOXX 600","benchmark":"EXW1.DE"}]}
```

**Step 4: Verify frontend**

Open your Vercel URL + `/backtest`. The config panel should appear. Run a quick backtest with default params and verify results display.

**Step 5: Final commit if needed**

If any fixes were needed in Steps 3-4, commit them:
```bash
git add -A && git commit -m "fix: backtest deployment fixes"
git push
```
