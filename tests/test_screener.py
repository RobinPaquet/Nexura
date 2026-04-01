import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from unittest.mock import MagicMock


def test_check_company_below_esg_min_returns_alert():
    from services.screener import _check_company
    company = {"totalScore": 25.0, "sector": "Technology"}
    alerts = _check_company(company, esg_min=50.0, sectors_exclude=[], coverage_min=0.0)
    assert len(alerts) == 1
    assert "25" in alerts[0] or "below" in alerts[0]


def test_check_company_above_esg_min_no_alert():
    from services.screener import _check_company
    company = {"totalScore": 75.0, "sector": "Technology"}
    alerts = _check_company(company, esg_min=50.0, sectors_exclude=[], coverage_min=0.0)
    assert alerts == []


def test_check_company_excluded_sector_returns_alert():
    from services.screener import _check_company
    company = {"totalScore": 80.0, "sector": "Oil & Gas"}
    alerts = _check_company(company, esg_min=0.0, sectors_exclude=["oil"], coverage_min=0.0)
    assert len(alerts) == 1
    assert "sector" in alerts[0].lower() or "oil" in alerts[0].lower()


def test_check_company_no_issues_no_alerts():
    from services.screener import _check_company
    company = {"totalScore": 80.0, "sector": "Technology"}
    alerts = _check_company(company, esg_min=50.0, sectors_exclude=["oil"], coverage_min=0.0)
    assert alerts == []
