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
