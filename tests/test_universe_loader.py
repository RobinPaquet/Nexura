import pytest
from data.universe_loader import load_universe, UNIVERSES, get_benchmark_ticker


def test_load_sp500_returns_tuple():
    tickers = load_universe("sp500")
    assert isinstance(tickers, tuple)
    assert len(tickers) > 10
    assert all(isinstance(t, str) for t in tickers)


def test_load_stoxx600_returns_tuple():
    tickers = load_universe("stoxx600")
    assert isinstance(tickers, tuple)
    assert len(tickers) > 10
    assert all(isinstance(t, str) for t in tickers)


def test_load_unknown_universe_raises():
    with pytest.raises(ValueError, match="Unknown universe"):
        load_universe("nasdaq")


def test_universes_constant_has_both():
    assert "sp500" in UNIVERSES
    assert "stoxx600" in UNIVERSES


def test_get_benchmark_ticker_sp500():
    assert get_benchmark_ticker("sp500") == "SPY"


def test_get_benchmark_ticker_stoxx600():
    assert get_benchmark_ticker("stoxx600") == "EXW1.DE"


def test_get_benchmark_ticker_unknown_raises():
    with pytest.raises(ValueError, match="Unknown universe"):
        get_benchmark_ticker("nasdaq")
