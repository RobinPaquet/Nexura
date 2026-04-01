# Backtest Module — Design Document

**Date:** 2026-04-01  
**Status:** Approved

---

## Goal

Build a professional ESG backtest engine into the Weefin Terminal. Users configure an ESG-filtered strategy on a fixed index universe, run a 5-year vectorized backtest with simulated transaction costs, and view results across 4 analytics tabs (Performance / Risk / Attribution / Trades).

---

## Architecture

Backtest runs entirely server-side (FastAPI). The frontend sends a POST request with strategy parameters and receives all results as JSON. No incremental streaming — results returned in one response after ~10–30s computation.

```
POST /backtest/run       → run backtest, return full results
GET  /backtest/universes → list available index universes
```

**Stack:**
- `pandas` + `numpy` — vectorized return calculations
- `yfinance` — historical OHLCV (batch download, cached in memory per request)
- `scipy` — Sharpe, Sortino, alpha/beta calculations
- `PyPortfolioOpt` — ESG-weighted portfolio optimization

---

## Strategy Logic

At each quarterly rebalancing date:

1. **Filter** — keep universe companies with ESG score ≥ `esg_min`, exclude specified sectors
2. **Score** — composite score = `0.7 × ESG_score_normalized + 0.3 × ESG_momentum_rank`
   - ESG momentum = percentile rank improvement vs previous quarter (synthetic, based on rank shuffle since static data)
3. **Weight** — weights proportional to composite score, top 50 holdings max
4. **Simulate** — apply 0.1% transaction cost per trade, compute turnover
5. **Benchmark** — compare vs SPY (S&P 500) or EXW1.DE (STOXX 600) via yfinance

---

## Universe Data

Two static JSON files in `data/`:
- `data/sp500_tickers.json` — 500 tickers with ISIN mapping
- `data/stoxx600_tickers.json` — 600 tickers with ISIN mapping

ESG scores come from existing static data (26,350 companies). Tickers without ESG data are excluded from the strategy portfolio but included in benchmark.

---

## Backtest Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `universe` | enum | `sp500` | `sp500` or `stoxx600` |
| `years` | int | 5 | Lookback period (1–5) |
| `esg_min` | float | 50 | Minimum ESG score (0–100) |
| `sectors_exclude` | list[str] | [] | Sectors to exclude |
| `esg_weighted` | bool | true | Weight by ESG score |
| `esg_momentum` | bool | false | Boost ESG improvers |

---

## Output Structure

```json
{
  "params": { ... },
  "summary": {
    "cagr": 0.124,
    "sharpe": 1.32,
    "max_drawdown": -0.187,
    "alpha": 0.034
  },
  "performance": {
    "dates": [...],
    "portfolio": [...],
    "benchmark": [...]
  },
  "risk": {
    "volatility": 0.142,
    "sharpe": 1.32,
    "sortino": 1.87,
    "calmar": 0.66,
    "beta": 0.91,
    "alpha": 0.034,
    "max_drawdown": -0.187,
    "drawdown_duration_days": 124,
    "rolling_sharpe": { "dates": [...], "values": [...] }
  },
  "attribution": {
    "top_contributors": [{ "ticker": "ASML", "contribution": 0.034 }, ...],
    "sector_weights": { "Technology": 0.32, ... },
    "esg_distribution": { "buckets": [0,20,40,60,80,100], "counts": [...] }
  },
  "trades": [
    { "date": "2020-03-31", "buys": [...], "sells": [...], "turnover": 0.23, "cost": 0.0018 }
  ]
}
```

---

## Frontend — Page `/backtest`

**Layout:** 2-column (1/3 config panel + 2/3 results)

**Config panel:**
- Universe dropdown (STOXX 600 / S&P 500)
- Period slider (1–5 years)
- ESG min slider (0–100)
- Sector exclusion buttons (same as scanner)
- ESG weighting toggle
- ESG momentum toggle
- "Lancer le backtest" button + loader

**Results area — 4 tabs:**
- **Performance** — equity curve (line chart: portfolio vs benchmark), CAGR, total return
- **Risk** — metrics table + rolling Sharpe chart
- **Attribution** — top contributors table, sector pie chart, ESG score distribution bar chart
- **Trades** — rebalancing log table (date, turnover %, cumulative costs)

**Always-visible summary bar** (above tabs): CAGR · Sharpe · Max DD · Alpha vs benchmark

**Charting library:** `recharts` (lightweight, Next.js compatible)  
**Colors:** teal for strategy, zinc-500 for benchmark (consistent with terminal design)

---

## Metrics Reference

| Metric | Formula |
|--------|---------|
| CAGR | `(final/initial)^(1/years) - 1` |
| Volatility | `std(daily_returns) × √252` |
| Sharpe | `(CAGR - 0.02) / volatility` (2% risk-free rate) |
| Sortino | `(CAGR - 0.02) / downside_std × √252` |
| Calmar | `CAGR / abs(max_drawdown)` |
| Beta | `cov(port, bench) / var(bench)` |
| Alpha | `CAGR - (rf + beta × (bench_CAGR - rf))` |
| Max Drawdown | `min((equity / cummax(equity)) - 1)` |

---

## Constraints & Limitations

- yfinance may return incomplete data for some tickers — missing tickers are silently skipped
- ESG momentum is synthetic (no true historical ESG time series available)
- No slippage model beyond flat 0.1% per trade
- Backtest is not survivorship-bias-free (uses current index composition)
- Computation time ~10–30s for full 5-year backtest on 500+ tickers
