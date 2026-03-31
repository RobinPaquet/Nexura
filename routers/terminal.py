from fastapi import APIRouter, HTTPException
from services.market_data import get_quote, get_ohlcv
from data.esg_loader import get_company_by_isin, search_companies

router = APIRouter(prefix="/terminal", tags=["terminal"])

@router.get("/quote/{symbol}")
async def quote(symbol: str):
    data = await get_quote(symbol.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return data

@router.get("/ohlcv/{symbol}")
async def ohlcv(symbol: str, from_date: str = "2024-01-01", to_date: str = "2024-12-31"):
    upper = symbol.upper()
    bars = await get_ohlcv(upper, from_date=from_date, to_date=to_date)
    return {"symbol": upper, "bars": bars}

@router.get("/search")
async def search(q: str, limit: int = 10):
    results = search_companies(q, limit=limit)
    return {"results": results, "count": len(results)}

@router.get("/company/{isin}")
async def company(isin: str):
    esg = get_company_by_isin(isin)
    if not esg:
        raise HTTPException(status_code=404, detail=f"Company {isin} not found")
    ticker = esg.get("ticker") or esg.get("symbol") or ""
    finance = await get_quote(ticker) if ticker else None
    return {"isin": isin, "esg": esg, "finance": finance}
