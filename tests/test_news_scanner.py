import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from unittest.mock import patch, MagicMock


def test_classify_with_rules_negative():
    from services.news_scanner import classify_with_rules
    sentiment, score = classify_with_rules("Company faces lawsuit over greenwashing claims")
    assert sentiment == "negative"
    assert score < 0


def test_classify_with_rules_positive():
    from services.news_scanner import classify_with_rules
    sentiment, score = classify_with_rules("Company achieves carbon neutral status ahead of schedule")
    assert sentiment == "positive"
    assert score > 0


def test_classify_with_rules_neutral():
    from services.news_scanner import classify_with_rules
    sentiment, score = classify_with_rules("Company announces quarterly earnings")
    assert sentiment == "neutral"
    assert score == 0.0


def test_build_gdelt_query():
    from services.news_scanner import _build_gdelt_url
    url = _build_gdelt_url("BNP Paribas")
    assert "BNP" in url
    assert "ESG" in url or "sustainability" in url


@pytest.mark.asyncio
async def test_fetch_esg_news_handles_empty_response():
    from services.news_scanner import fetch_esg_news
    with patch("services.news_scanner.SessionLocal") as mock_session:
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        mock_session.return_value = mock_db

        await fetch_esg_news()
        mock_db.commit.assert_called_once()
