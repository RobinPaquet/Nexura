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


@router.get("/debug")
def debug():
    import yfinance as yf, pandas as pd
    from datetime import datetime, timedelta
    end = datetime.today()
    start = end - timedelta(days=400)
    raw = yf.download(["AAPL", "SPY"], start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), auto_adjust=True, progress=False, threads=False)
    prices_shape = list(raw.shape)
    has_tz = str(getattr(raw.index, "tz", None))
    cols = str(raw.columns.tolist()[:4])
    rebal = pd.date_range(start=start, end=end, freq="QS")
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw
    if hasattr(prices.index, "tz") and prices.index.tz is not None:
        prices.index = prices.index.tz_convert(None)
    period_prices = prices.loc[rebal[0]:rebal[1]] if len(rebal) >= 2 else pd.DataFrame()
    return {
        "prices_shape": prices_shape,
        "tz": has_tz,
        "columns": cols,
        "rebal_dates": [str(r) for r in rebal],
        "period_prices_len": len(period_prices),
        "prices_index_sample": [str(d) for d in prices.index[:3]],
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
