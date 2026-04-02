from __future__ import annotations

import hashlib
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
            # TODO: replace with real ESG score time-series when historical data is available
            # Currently uses a deterministic synthetic rank based on ticker name as a placeholder
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
    start_date = end_date - timedelta(days=365 * years + 30)

    # Batch download prices
    raw = yf.download(
        all_tickers,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        auto_adjust=True,
        progress=False,
    )

    # yfinance returns MultiIndex (Close, ticker) if multiple tickers
    # or a flat DataFrame with ticker columns (e.g. from mocks or newer yfinance)
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    elif "Close" in raw.columns:
        # Single-ticker download: one "Close" column
        prices = raw[["Close"]].rename(columns={"Close": all_tickers[0]})
    else:
        # Already a flat ticker-keyed DataFrame (e.g. from test mocks)
        prices = raw

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
            "dates": [str(d.date()) for d in port_series.index],
            "portfolio": [round(v, 4) for v in port_series.values],
            "benchmark": [round(v, 4) for v in bench_series.values],
        },
        "risk": metrics,
        "attribution": attribution,
        "trades": equity_curve["trades"],
    }


def filter_companies(
    companies: list,
    universe_tickers,
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
        port_segment = (1 + port_daily).cumprod()

        # Benchmark daily returns
        if benchmark_ticker in prices.columns:
            bench_daily = period_prices[benchmark_ticker].pct_change().dropna()
            bench_segment = (1 + bench_daily).cumprod()
        else:
            bench_segment = pd.Series(np.ones(len(port_segment)), index=period_returns.index)

        common = period_returns.index
        bench_segment = bench_segment.reindex(common).ffill().bfill()

        dates_in_period = [str(d.date()) for d in common]
        # Cost is paid once at rebalance, applied to portfolio_value before the period
        portfolio_value_after_cost = portfolio_value * (1 - cost)
        port_vals_in_period = [float(v) * portfolio_value_after_cost for v in port_segment]
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

    sector_weights: dict = {}
    total_score = sum(c.get("composite_score", 50) for c in filtered)
    for c in filtered:
        sector = str(c.get("sector") or c.get("industry") or "Other")
        weight = c.get("composite_score", 50) / total_score if total_score > 0 else 0
        sector_weights[sector] = round(sector_weights.get(sector, 0) + weight, 4)

    scores = [float(c.get("score") or c.get("totalScore") or 0) for c in filtered]
    buckets = [0, 20, 40, 60, 80, 100]
    counts = [0] * (len(buckets) - 1)
    for s in scores:
        for j in range(len(buckets) - 1):
            if buckets[j] <= s < buckets[j + 1]:
                counts[j] += 1
                break
        else:
            counts[-1] += 1

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
