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
