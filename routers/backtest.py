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
