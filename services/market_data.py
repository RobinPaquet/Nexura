import httpx
import os
from typing import Optional
import yfinance as yf

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
POLYGON_BASE = "https://api.polygon.io"

async def get_quote(symbol: str) -> Optional[dict]:
    """Fetch latest price. Uses Polygon.io if API key available, else yfinance fallback."""
    if POLYGON_API_KEY:
        result = await _get_quote_polygon(symbol)
        if result:
            return result
    return _get_quote_yfinance(symbol)

async def _get_quote_polygon(symbol: str) -> Optional[dict]:
    url = f"{POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params={"apiKey": POLYGON_API_KEY}, timeout=5.0)
            if r.status_code == 200:
                ticker_data = r.json().get("ticker", {})
                day = ticker_data.get("day", {})
                prev = ticker_data.get("prevDay", {})
                close = day.get("c", 0)
                prev_close = prev.get("c", 1)
                change = round(close - prev_close, 2)
                change_pct = round((change / prev_close * 100) if prev_close else 0, 2)
                return {
                    "symbol": symbol,
                    "price": close,
                    "change": change,
                    "change_pct": change_pct,
                    "volume": day.get("v", 0),
                    "market_cap": None,
                    "delayed": True,
                }
        except Exception:
            pass
    return None

def _get_quote_yfinance(symbol: str) -> Optional[dict]:
    """Fallback: yfinance (unofficial, rate-limited)."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change = round(price - prev, 2)
        change_pct = round((change / prev * 100) if prev else 0, 2)
        info = ticker.fast_info
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": change,
            "change_pct": change_pct,
            "volume": int(getattr(info, "three_month_average_volume", 0) or 0),
            "market_cap": int(info.market_cap) if getattr(info, "market_cap", None) else None,
            "delayed": True,
        }
    except Exception:
        return None

async def get_ohlcv(symbol: str, from_date: str = "2024-01-01", to_date: str = "2024-12-31") -> list[dict]:
    """Get OHLCV bars. Uses Polygon.io if key available, else yfinance."""
    if POLYGON_API_KEY:
        result = await _get_ohlcv_polygon(symbol, from_date, to_date)
        if result:
            return result
    return _get_ohlcv_yfinance(symbol)

async def _get_ohlcv_polygon(symbol: str, from_date: str, to_date: str) -> list[dict]:
    url = f"{POLYGON_BASE}/v2/aggs/ticker/{symbol}/range/1/day/{from_date}/{to_date}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                url,
                params={"apiKey": POLYGON_API_KEY, "adjusted": "true", "sort": "asc", "limit": 365},
                timeout=10.0,
            )
            if r.status_code == 200:
                return [
                    {"t": b["t"], "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
                    for b in r.json().get("results", [])
                ]
        except Exception:
            pass
    return []

def _get_ohlcv_yfinance(symbol: str) -> list[dict]:
    try:
        hist = yf.Ticker(symbol).history(period="1y")
        return [
            {
                "t": int(ts.timestamp() * 1000),
                "o": round(float(row["Open"]), 2),
                "h": round(float(row["High"]), 2),
                "l": round(float(row["Low"]), 2),
                "c": round(float(row["Close"]), 2),
                "v": int(row["Volume"]),
            }
            for ts, row in hist.iterrows()
        ]
    except Exception:
        return []
