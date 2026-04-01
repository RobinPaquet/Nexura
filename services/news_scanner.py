import os
import httpx
from models.watchlist import SessionLocal, WatchlistItem
from models.scanner import ScannerAlert

GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

POSITIVE_KEYWORDS = [
    "carbon neutral", "net zero", "renewable energy", "sustainability award",
    "esg leader", "clean energy", "green bond", "climate target", "net-zero",
]
NEGATIVE_KEYWORDS = [
    "greenwashing", "lawsuit", "violation", "scandal", "fine", "fraud",
    "emissions fraud", "environmental breach", "human rights violation",
    "bribery", "corruption",
]


def classify_with_rules(title: str) -> tuple[str, float]:
    text = title.lower()
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    if neg > 0:
        return "negative", round(-(0.5 + neg * 0.3), 2)
    if pos > 0:
        return "positive", round(0.5 + pos * 0.3, 2)
    return "neutral", 0.0


def _build_gdelt_url(company_name: str) -> str:
    return (
        f"{GDELT_BASE}?query={company_name}+ESG+sustainability"
        f"&mode=artlist&maxrecords=10&format=json&timespan=1440"
    )


async def _classify(title: str) -> tuple[str, float]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return await _classify_with_haiku(title, api_key)
        except Exception:
            pass
    return classify_with_rules(title)


async def _classify_with_haiku(title: str, api_key: str) -> tuple[str, float]:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{
            "role": "user",
            "content": (
                f'Classify the ESG sentiment of this headline. '
                f'Reply ONLY with: POSITIVE 0.X or NEGATIVE -0.X or NEUTRAL 0.0\n'
                f'Headline: "{title}"'
            ),
        }],
    )
    text = msg.content[0].text.strip().upper()
    if text.startswith("POSITIVE"):
        return "positive", float(text.split()[1])
    if text.startswith("NEGATIVE"):
        return "negative", float(text.split()[1])
    return "neutral", 0.0


async def fetch_esg_news():
    db = SessionLocal()
    try:
        watchlist = db.query(WatchlistItem).all()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for item in watchlist:
                url = _build_gdelt_url(item.name)
                try:
                    r = await client.get(url)
                    if r.status_code != 200:
                        continue
                    articles = r.json().get("articles") or []
                except Exception:
                    continue

                for article in articles:
                    title = article.get("title", "")
                    if not title:
                        continue

                    sentiment, score = await _classify(title)

                    if sentiment == "neutral":
                        continue

                    existing = (
                        db.query(ScannerAlert)
                        .filter(
                            ScannerAlert.isin == item.isin,
                            ScannerAlert.headline == title,
                        )
                        .first()
                    )
                    if existing:
                        continue

                    db.add(ScannerAlert(
                        isin=item.isin,
                        company=item.name,
                        type="news",
                        sentiment=sentiment,
                        headline=title,
                        source_url=article.get("url"),
                        score=score,
                    ))

        db.commit()
    finally:
        db.close()
