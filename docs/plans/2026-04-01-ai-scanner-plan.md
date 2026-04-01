# AI Scanner (Phase 2) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ajouter un AI Scanner au Weefin Terminal — Layer 1 (screener ESG par règles) + Layer 2 (signaux news ESG via GDELT), avec notifications in-app.

**Architecture:** Celery Beat tourne deux tâches en arrière-plan (screener toutes les 15 min, news toutes les heures). Redis est le broker Celery. Les alertes sont stockées en PostgreSQL et exposées via FastAPI. Le frontend poll `/scanner/alerts` toutes les 60s.

**Tech Stack:** FastAPI, Celery 5.4, Redis 7, SQLAlchemy 2, httpx, anthropic (optionnel), Next.js 14 App Router, TypeScript, Tailwind CSS

---

## Contexte codebase

**weefin-api** (`/Users/robin/Desktop/Weefinnn/weefin-api/`) :
- `main.py` — FastAPI app, inclut les routers
- `models/watchlist.py` — SQLAlchemy Base + engine + WatchlistItem + get_db()
- `routers/watchlist.py` — pattern à suivre pour les nouveaux routers
- `tests/test_watchlist.py` — pattern de test à suivre (dependency_overrides)
- `tests/conftest.py` — `os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")` + fixture ESG_DATA_PATH
- `docker-compose.yml` — PostgreSQL + Redis déjà définis
- `requirements.txt` — celery, redis déjà présents

**weefin-terminal** (`/Users/robin/Desktop/Weefinnn/weefin-terminal/`) :
- `src/lib/api.ts` — fonctions fetch vers le backend
- `src/app/page.tsx` — page principale avec header WEEFIN TERMINAL
- `src/components/` — EsgScoreBlock, FinanceBlock, PriceChart, SearchBar

---

## Task 1 : Ajouter le package anthropic

**Files:**
- Modify: `requirements.txt`

**Step 1: Ajouter anthropic à requirements.txt**

```
# Requires Python 3.11+
fastapi==0.111.0
uvicorn[standard]==0.30.1
httpx==0.27.0
yfinance==0.2.40
pandas==2.2.2
python-dotenv==1.0.1
python-multipart==0.0.9
redis==5.0.6
celery==5.4.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.30
pytest==8.2.2
pytest-asyncio==0.23.7
anyio==4.4.0
anthropic==0.31.0
```

**Step 2: Installer localement**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-api
.venv/bin/pip install anthropic==0.31.0
```

Expected: `Successfully installed anthropic-0.31.0`

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add anthropic package for future Haiku NLP"
```

---

## Task 2 : Celery app

**Files:**
- Create: `celery_app.py`

**Step 1: Écrire le test**

```python
# tests/test_celery_app.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

def test_celery_app_loads():
    from celery_app import celery
    assert celery.main == "weefin"

def test_celery_beat_schedule_has_two_tasks():
    from celery_app import celery
    schedule = celery.conf.beat_schedule
    assert "run-screener" in schedule
    assert "fetch-esg-news" in schedule

def test_run_screener_scheduled_every_15_min():
    from celery_app import celery
    task = celery.conf.beat_schedule["run-screener"]
    assert task["schedule"] == 900.0

def test_fetch_esg_news_scheduled_every_hour():
    from celery_app import celery
    task = celery.conf.beat_schedule["fetch-esg-news"]
    assert task["schedule"] == 3600.0
```

**Step 2: Vérifier que le test échoue**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-api
.venv/bin/pytest tests/test_celery_app.py -v
```

Expected: FAIL avec `ModuleNotFoundError: No module named 'celery_app'`

**Step 3: Créer celery_app.py**

```python
# celery_app.py
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "weefin",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],
)

celery.conf.beat_schedule = {
    "run-screener": {
        "task": "tasks.run_screener_task",
        "schedule": 900.0,  # 15 minutes
    },
    "fetch-esg-news": {
        "task": "tasks.fetch_esg_news_task",
        "schedule": 3600.0,  # 1 heure
    },
}
celery.conf.timezone = "UTC"
```

**Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_celery_app.py -v
```

Expected: 4 PASSED

**Step 5: Commit**

```bash
git add celery_app.py tests/test_celery_app.py
git commit -m "feat: add Celery app with beat schedule"
```

---

## Task 3 : Modèles DB scanner

**Files:**
- Create: `models/scanner.py`
- Modify: `main.py`

**Step 1: Écrire les tests**

```python
# tests/test_scanner_models.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

def test_scanner_alert_model_has_required_fields():
    from models.scanner import ScannerAlert
    cols = {c.name for c in ScannerAlert.__table__.columns}
    assert {"id", "isin", "company", "type", "sentiment", "headline", "source_url", "score", "created_at"} <= cols

def test_scanner_config_model_has_required_fields():
    from models.scanner import ScannerConfig
    cols = {c.name for c in ScannerConfig.__table__.columns}
    assert {"id", "esg_min", "sectors_exclude", "countries", "coverage_min", "updated_at"} <= cols

def test_create_scanner_tables_runs_without_error():
    from models.scanner import create_scanner_tables
    create_scanner_tables()  # must not raise
```

**Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_scanner_models.py -v
```

Expected: FAIL avec `ModuleNotFoundError: No module named 'models.scanner'`

**Step 3: Créer models/scanner.py**

```python
# models/scanner.py
from sqlalchemy import Column, String, Float, DateTime, Integer
from datetime import datetime, timezone
from models.watchlist import Base, engine


class ScannerAlert(Base):
    __tablename__ = "scanner_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    isin = Column(String, nullable=False)
    company = Column(String, nullable=False)
    type = Column(String, nullable=False)       # 'screener' | 'news'
    sentiment = Column(String, nullable=True)   # 'positive' | 'negative' | 'neutral'
    headline = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ScannerConfig(Base):
    __tablename__ = "scanner_config"

    id = Column(Integer, primary_key=True, default=1)
    esg_min = Column(Float, default=0.0)
    sectors_exclude = Column(String, default="")  # comma-separated
    countries = Column(String, default="")         # comma-separated, empty = all
    coverage_min = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def create_scanner_tables():
    Base.metadata.create_all(bind=engine)
```

**Step 4: Appeler create_scanner_tables au démarrage — modifier main.py**

Ajouter après les imports des routers existants :

```python
# main.py — ajouter ces deux lignes après les includes de routers existants
from models.scanner import create_scanner_tables as create_scanner_tables_fn
create_scanner_tables_fn()
```

Le fichier `main.py` complet devient :

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

VERSION = "0.1.0"

app = FastAPI(title="Weefin API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.terminal import router as terminal_router
app.include_router(terminal_router)

from routers.watchlist import router as watchlist_router
app.include_router(watchlist_router)

from models.scanner import create_scanner_tables as create_scanner_tables_fn
create_scanner_tables_fn()

@app.get("/health")
async def health():
    return {"status": "ok", "version": VERSION}
```

**Step 5: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_scanner_models.py -v
```

Expected: 3 PASSED

**Step 6: Commit**

```bash
git add models/scanner.py main.py tests/test_scanner_models.py
git commit -m "feat: add scanner DB models (ScannerAlert, ScannerConfig)"
```

---

## Task 4 : Layer 1 — Service screener

**Files:**
- Create: `services/screener.py`
- Create: `tests/test_screener.py`

Le screener parcourt les entreprises de la watchlist, applique les filtres ESG depuis ScannerConfig, et insère une alerte pour chaque entreprise qui sort des critères.

**Step 1: Écrire les tests**

```python
# tests/test_screener.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from unittest.mock import MagicMock, patch


def make_mock_db(watchlist_items=None, config=None, existing_alert=None):
    db = MagicMock()
    db.query.return_value.all.return_value = watchlist_items or []
    db.query.return_value.filter.return_value.first.return_value = config
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = existing_alert
    return db


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
```

**Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_screener.py -v
```

Expected: FAIL avec `ModuleNotFoundError: No module named 'services.screener'`

**Step 3: Créer services/screener.py**

```python
# services/screener.py
from models.watchlist import SessionLocal, WatchlistItem
from models.scanner import ScannerAlert, ScannerConfig
from data.esg_loader import get_company_by_isin
from datetime import datetime, timezone


EXCLUSION_KEYWORDS = {
    "charbon": ["coal", "mining"],
    "armes": ["defense", "weapons", "arms"],
    "tabac": ["tobacco"],
    "petrole": ["oil", "gas", "fossil"],
}


def run_screener():
    db = SessionLocal()
    try:
        config = db.query(ScannerConfig).filter(ScannerConfig.id == 1).first()
        esg_min = config.esg_min if config else 0.0
        sectors_exclude = (
            [s.strip().lower() for s in config.sectors_exclude.split(",") if s.strip()]
            if config else []
        )
        coverage_min = config.coverage_min if config else 0.0

        watchlist = db.query(WatchlistItem).all()

        for item in watchlist:
            company = get_company_by_isin(item.isin)
            if not company:
                continue

            alert_messages = _check_company(company, esg_min, sectors_exclude, coverage_min)
            for msg in alert_messages:
                existing = (
                    db.query(ScannerAlert)
                    .filter(
                        ScannerAlert.isin == item.isin,
                        ScannerAlert.type == "screener",
                        ScannerAlert.headline == msg,
                    )
                    .order_by(ScannerAlert.created_at.desc())
                    .first()
                )
                if not existing:
                    db.add(ScannerAlert(
                        isin=item.isin,
                        company=item.name,
                        type="screener",
                        headline=msg,
                        sentiment="negative",
                        score=None,
                        source_url=None,
                    ))

        db.commit()
    finally:
        db.close()


def _check_company(company: dict, esg_min: float, sectors_exclude: list, coverage_min: float) -> list[str]:
    alerts = []

    score = company.get("totalScore") or company.get("score") or 0
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0

    if score < esg_min:
        alerts.append(f"ESG score {score:.1f} below minimum {esg_min:.1f}")

    sector = str(company.get("sector") or company.get("industry") or "").lower()
    for excl in sectors_exclude:
        if excl in sector:
            alerts.append(f"Sector '{sector}' matches exclusion '{excl}'")
            break

    return alerts
```

**Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_screener.py -v
```

Expected: 4 PASSED

**Step 5: Commit**

```bash
git add services/screener.py tests/test_screener.py
git commit -m "feat: add screener service (Layer 1)"
```

---

## Task 5 : Layer 2 — Service news scanner

**Files:**
- Create: `services/news_scanner.py`
- Create: `tests/test_news_scanner.py`

**Step 1: Écrire les tests**

```python
# tests/test_news_scanner.py
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

        # No watchlist items → no HTTP calls, no error
        await fetch_esg_news()
        mock_db.commit.assert_called_once()
```

**Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_news_scanner.py -v
```

Expected: FAIL avec `ModuleNotFoundError: No module named 'services.news_scanner'`

**Step 3: Créer services/news_scanner.py**

```python
# services/news_scanner.py
import os
import httpx
from models.watchlist import SessionLocal, WatchlistItem
from models.scanner import ScannerAlert
from datetime import datetime, timezone

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
    query = f"{company_name} ESG sustainability"
    return (
        f"{GDELT_BASE}?query={httpx.QueryParams({'q': query})}"
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
                company_name = item.name
                url = (
                    f"{GDELT_BASE}?query={company_name}+ESG+sustainability"
                    f"&mode=artlist&maxrecords=10&format=json&timespan=1440"
                )
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

                    # Skip neutral low-signal articles
                    if sentiment == "neutral":
                        continue

                    # Skip if identical alert already exists
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
                        company=company_name,
                        type="news",
                        sentiment=sentiment,
                        headline=title,
                        source_url=article.get("url"),
                        score=score,
                    ))

        db.commit()
    finally:
        db.close()


def _build_gdelt_url(company_name: str) -> str:
    return (
        f"{GDELT_BASE}?query={company_name}+ESG+sustainability"
        f"&mode=artlist&maxrecords=10&format=json&timespan=1440"
    )
```

**Step 4: Vérifier que les tests passent**

```bash
.venv/bin/pytest tests/test_news_scanner.py -v
```

Expected: 5 PASSED

**Step 5: Commit**

```bash
git add services/news_scanner.py tests/test_news_scanner.py
git commit -m "feat: add GDELT news scanner service (Layer 2)"
```

---

## Task 6 : Tâches Celery

**Files:**
- Create: `tasks.py`

Les tâches Celery sont de simples wrappers autour des services. Pas de tests unitaires ici (tester Celery nécessite un broker Redis réel — hors scope).

**Step 1: Créer tasks.py**

```python
# tasks.py
import asyncio
from celery_app import celery
from services.screener import run_screener
from services.news_scanner import fetch_esg_news


@celery.task(name="tasks.run_screener_task")
def run_screener_task():
    run_screener()


@celery.task(name="tasks.fetch_esg_news_task")
def fetch_esg_news_task():
    asyncio.run(fetch_esg_news())
```

**Step 2: Vérifier que tasks.py importe sans erreur**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-api
.venv/bin/python -c "import tasks; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add tasks.py
git commit -m "feat: add Celery tasks wrapping screener and news scanner"
```

---

## Task 7 : Router scanner

**Files:**
- Create: `routers/scanner.py`
- Modify: `main.py`
- Create: `tests/test_scanner_router.py`

**Step 1: Écrire les tests**

```python
# tests/test_scanner_router.py
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock
from main import app
from models.watchlist import get_db
from models.scanner import ScannerAlert, ScannerConfig
from datetime import datetime, timezone


def make_mock_db(alerts=None, config=None):
    db = MagicMock()

    def query_side_effect(model):
        m = MagicMock()
        if model is ScannerAlert:
            m.order_by.return_value.limit.return_value.all.return_value = alerts or []
        elif model is ScannerConfig:
            m.filter.return_value.first.return_value = config
        return m

    db.query.side_effect = query_side_effect
    return db


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_get_alerts_empty():
    mock_db = make_mock_db(alerts=[])
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/scanner/alerts")
    assert r.status_code == 200
    assert r.json() == {"alerts": [], "count": 0}


@pytest.mark.asyncio
async def test_get_alerts_returns_list():
    alert = MagicMock(spec=ScannerAlert)
    alert.id = 1
    alert.isin = "FR0000131104"
    alert.company = "BNP Paribas"
    alert.type = "news"
    alert.sentiment = "negative"
    alert.headline = "BNP faces greenwashing lawsuit"
    alert.source_url = "https://example.com"
    alert.score = -0.8
    alert.created_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

    mock_db = make_mock_db(alerts=[alert])
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/scanner/alerts")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["alerts"][0]["isin"] == "FR0000131104"


@pytest.mark.asyncio
async def test_get_config_no_config_returns_defaults():
    mock_db = make_mock_db(config=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/scanner/config")
    assert r.status_code == 200
    body = r.json()
    assert body["esg_min"] == 0.0
    assert body["sectors_exclude"] == []


@pytest.mark.asyncio
async def test_save_config_returns_ok():
    mock_db = make_mock_db(config=None)
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/scanner/config", json={
            "esg_min": 60.0,
            "sectors_exclude": ["oil", "coal"],
            "countries": [],
            "coverage_min": 0.5,
        })
    assert r.status_code == 200
    assert r.json()["status"] == "saved"
```

**Step 2: Vérifier que les tests échouent**

```bash
.venv/bin/pytest tests/test_scanner_router.py -v
```

Expected: FAIL (router non enregistré)

**Step 3: Créer routers/scanner.py**

```python
# routers/scanner.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from models.watchlist import get_db
from models.scanner import ScannerAlert, ScannerConfig

router = APIRouter(prefix="/scanner", tags=["scanner"])


class ConfigRequest(BaseModel):
    esg_min: float = 0.0
    sectors_exclude: list[str] = []
    countries: list[str] = []
    coverage_min: float = 0.0


@router.get("/alerts")
def get_alerts(limit: int = 50, db: Session = Depends(get_db)):
    alerts = (
        db.query(ScannerAlert)
        .order_by(ScannerAlert.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "alerts": [
            {
                "id": a.id,
                "isin": a.isin,
                "company": a.company,
                "type": a.type,
                "sentiment": a.sentiment,
                "headline": a.headline,
                "source_url": a.source_url,
                "score": a.score,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ],
        "count": len(alerts),
    }


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    config = db.query(ScannerConfig).filter(ScannerConfig.id == 1).first()
    if not config:
        return {
            "esg_min": 0.0,
            "sectors_exclude": [],
            "countries": [],
            "coverage_min": 0.0,
        }
    return {
        "esg_min": config.esg_min,
        "sectors_exclude": [s for s in config.sectors_exclude.split(",") if s],
        "countries": [c for c in config.countries.split(",") if c],
        "coverage_min": config.coverage_min,
    }


@router.post("/config")
def save_config(req: ConfigRequest, db: Session = Depends(get_db)):
    config = db.query(ScannerConfig).filter(ScannerConfig.id == 1).first()
    if config:
        config.esg_min = req.esg_min
        config.sectors_exclude = ",".join(req.sectors_exclude)
        config.countries = ",".join(req.countries)
        config.coverage_min = req.coverage_min
        config.updated_at = datetime.now(timezone.utc)
    else:
        config = ScannerConfig(
            id=1,
            esg_min=req.esg_min,
            sectors_exclude=",".join(req.sectors_exclude),
            countries=",".join(req.countries),
            coverage_min=req.coverage_min,
        )
        db.add(config)
    db.commit()
    return {"status": "saved"}
```

**Step 4: Enregistrer le router dans main.py**

Ajouter après les imports des autres routers :

```python
from routers.scanner import router as scanner_router
app.include_router(scanner_router)
```

Le fichier `main.py` complet devient :

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

VERSION = "0.1.0"

app = FastAPI(title="Weefin API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.terminal import router as terminal_router
app.include_router(terminal_router)

from routers.watchlist import router as watchlist_router
app.include_router(watchlist_router)

from routers.scanner import router as scanner_router
app.include_router(scanner_router)

from models.scanner import create_scanner_tables as create_scanner_tables_fn
create_scanner_tables_fn()

@app.get("/health")
async def health():
    return {"status": "ok", "version": VERSION}
```

**Step 5: Lancer tous les tests**

```bash
.venv/bin/pytest tests/test_scanner_router.py -v
```

Expected: 4 PASSED

**Step 6: Lancer la suite complète pour vérifier aucune régression**

```bash
.venv/bin/pytest -v
```

Expected: tous PASSED

**Step 7: Commit**

```bash
git add routers/scanner.py main.py tests/test_scanner_router.py
git commit -m "feat: add scanner router (/scanner/alerts, /scanner/config)"
```

---

## Task 8 : Frontend — api.ts additions

**Files:**
- Modify: `src/lib/api.ts` (`/Users/robin/Desktop/Weefinnn/weefin-terminal/src/lib/api.ts`)

**Step 1: Ajouter les fonctions scanner à api.ts**

Le fichier complet devient :

```typescript
// src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchQuote(symbol: string) {
  const res = await fetch(`${API_URL}/terminal/quote/${symbol}`);
  if (!res.ok) throw new Error(`Quote not found: ${symbol}`);
  return res.json();
}

export async function fetchCompany(isin: string) {
  const res = await fetch(`${API_URL}/terminal/company/${isin}`);
  if (!res.ok) throw new Error(`Company not found: ${isin}`);
  return res.json();
}

export async function fetchOHLCV(symbol: string, fromDate: string, toDate: string) {
  const res = await fetch(
    `${API_URL}/terminal/ohlcv/${symbol}?from_date=${fromDate}&to_date=${toDate}`
  );
  if (!res.ok) throw new Error(`OHLCV not found: ${symbol}`);
  return res.json();
}

export async function searchCompanies(query: string, limit = 10) {
  const res = await fetch(
    `${API_URL}/terminal/search?q=${encodeURIComponent(query)}&limit=${limit}`
  );
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function fetchAlerts(limit = 50) {
  const res = await fetch(`${API_URL}/scanner/alerts?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function fetchScannerConfig() {
  const res = await fetch(`${API_URL}/scanner/config`);
  if (!res.ok) throw new Error("Failed to fetch scanner config");
  return res.json();
}

export async function saveScannerConfig(config: {
  esg_min: number;
  sectors_exclude: string[];
  countries: string[];
  coverage_min: number;
}) {
  const res = await fetch(`${API_URL}/scanner/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Failed to save scanner config");
  return res.json();
}
```

**Step 2: Vérifier que le build TypeScript passe**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-terminal
npm run build 2>&1 | tail -5
```

Expected: `✓ Compiled successfully` (ou similaire)

**Step 3: Commit**

```bash
git add src/lib/api.ts
git commit -m "feat: add scanner API functions to api.ts"
```

---

## Task 9 : Frontend — Page /scanner

**Files:**
- Create: `src/app/scanner/page.tsx`
- Create: `src/components/AlertFeed.tsx`
- Create: `src/components/ScannerConfigPanel.tsx`

**Step 1: Créer src/components/AlertFeed.tsx**

```tsx
// src/components/AlertFeed.tsx
"use client";

interface Alert {
  id: number;
  isin: string;
  company: string;
  type: string;
  sentiment: string | null;
  headline: string | null;
  source_url: string | null;
  score: number | null;
  created_at: string | null;
}

interface AlertFeedProps {
  alerts: Alert[];
}

function sentimentColor(sentiment: string | null) {
  if (sentiment === "positive") return "text-emerald-400";
  if (sentiment === "negative") return "text-red-400";
  return "text-zinc-400";
}

function sentimentLabel(sentiment: string | null) {
  if (sentiment === "positive") return "↑ positif";
  if (sentiment === "negative") return "↓ négatif";
  return "— neutre";
}

export default function AlertFeed({ alerts }: AlertFeedProps) {
  if (alerts.length === 0) {
    return (
      <div className="text-zinc-600 text-sm text-center py-12">
        Aucune alerte pour l'instant.<br />
        Ajoutez des entreprises à votre watchlist.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {alerts.map((a) => (
        <div
          key={a.id}
          className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex flex-col gap-1"
        >
          <div className="flex items-center justify-between">
            <span className="text-zinc-200 text-sm font-medium">{a.company}</span>
            <span className={`text-xs font-mono ${sentimentColor(a.sentiment)}`}>
              {sentimentLabel(a.sentiment)}
            </span>
          </div>
          <p className="text-zinc-400 text-xs leading-snug">{a.headline}</p>
          <div className="flex items-center justify-between mt-1">
            <span className="text-zinc-600 text-xs">
              {a.type === "news" ? "News" : "Screener"} · {a.isin}
            </span>
            <div className="flex items-center gap-2">
              {a.source_url && (
                <a
                  href={a.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-teal-500 text-xs hover:underline"
                >
                  Source →
                </a>
              )}
              <span className="text-zinc-700 text-xs">
                {a.created_at ? new Date(a.created_at).toLocaleString("fr-FR") : ""}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Step 2: Créer src/components/ScannerConfigPanel.tsx**

```tsx
// src/components/ScannerConfigPanel.tsx
"use client";
import { useState } from "react";
import { saveScannerConfig } from "@/lib/api";

interface Config {
  esg_min: number;
  sectors_exclude: string[];
  coverage_min: number;
}

interface ScannerConfigPanelProps {
  config: Config;
  onSaved: () => void;
}

const SECTOR_OPTIONS = ["oil", "coal", "gas", "defense", "tobacco", "weapons"];

export default function ScannerConfigPanel({ config, onSaved }: ScannerConfigPanelProps) {
  const [esgMin, setEsgMin] = useState(config.esg_min);
  const [excluded, setExcluded] = useState<string[]>(config.sectors_exclude);
  const [coverageMin, setCoverageMin] = useState(config.coverage_min);
  const [saving, setSaving] = useState(false);

  function toggleSector(s: string) {
    setExcluded((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
  }

  async function handleSave() {
    setSaving(true);
    try {
      await saveScannerConfig({
        esg_min: esgMin,
        sectors_exclude: excluded,
        countries: [],
        coverage_min: coverageMin,
      });
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 flex flex-col gap-4">
      <h2 className="text-zinc-200 text-sm font-semibold uppercase tracking-wide">
        Filtres du screener
      </h2>

      <div>
        <label className="text-zinc-400 text-xs mb-1 block">
          Score ESG minimum : <span className="text-teal-400 font-mono">{esgMin}</span>
        </label>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={esgMin}
          onChange={(e) => setEsgMin(Number(e.target.value))}
          className="w-full accent-teal-500"
        />
      </div>

      <div>
        <label className="text-zinc-400 text-xs mb-2 block">Secteurs exclus</label>
        <div className="flex flex-wrap gap-2">
          {SECTOR_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => toggleSector(s)}
              className={`px-2 py-1 rounded text-xs border ${
                excluded.includes(s)
                  ? "bg-red-900/40 border-red-700 text-red-300"
                  : "border-zinc-700 text-zinc-500 hover:border-zinc-500"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-zinc-400 text-xs mb-1 block">
          Couverture données min : <span className="text-teal-400 font-mono">{coverageMin.toFixed(1)}</span>
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={coverageMin}
          onChange={(e) => setCoverageMin(Number(e.target.value))}
          className="w-full accent-teal-500"
        />
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs font-medium py-2 rounded"
      >
        {saving ? "Sauvegarde…" : "Appliquer les filtres"}
      </button>
    </div>
  );
}
```

**Step 3: Créer src/app/scanner/page.tsx**

```tsx
// src/app/scanner/page.tsx
"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import AlertFeed from "@/components/AlertFeed";
import ScannerConfigPanel from "@/components/ScannerConfigPanel";
import { fetchAlerts, fetchScannerConfig } from "@/lib/api";

interface Alert {
  id: number;
  isin: string;
  company: string;
  type: string;
  sentiment: string | null;
  headline: string | null;
  source_url: string | null;
  score: number | null;
  created_at: string | null;
}

interface Config {
  esg_min: number;
  sectors_exclude: string[];
  coverage_min: number;
}

const DEFAULT_CONFIG: Config = { esg_min: 0, sectors_exclude: [], coverage_min: 0 };

export default function ScannerPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [config, setConfig] = useState<Config>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [alertsData, configData] = await Promise.all([
        fetchAlerts(50),
        fetchScannerConfig(),
      ]);
      setAlerts(alertsData.alerts);
      setConfig(configData);
    } catch {
      // silently continue on error
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 60_000);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-4">
        <Link href="/" className="text-teal-400 font-bold text-lg tracking-tight hover:text-teal-300">
          WEEFIN
        </Link>
        <span className="text-zinc-600 text-sm">TERMINAL</span>
        <nav className="flex items-center gap-4 ml-4">
          <Link href="/" className="text-zinc-500 text-sm hover:text-zinc-300">
            Terminal
          </Link>
          <span className="text-teal-400 text-sm font-medium">Scanner</span>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {alerts.length > 0 && (
            <span className="bg-teal-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              {alerts.length}
            </span>
          )}
        </div>
      </header>

      <div className="p-6 max-w-5xl mx-auto">
        <h1 className="text-zinc-200 text-base font-semibold mb-4">AI Scanner ESG</h1>

        {loading ? (
          <div className="text-zinc-400 text-sm text-center py-12">Chargement…</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1">
              <ScannerConfigPanel config={config} onSaved={loadData} />
            </div>
            <div className="md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-zinc-400 text-xs uppercase tracking-wide">
                  Alertes récentes
                </h2>
                <span className="text-zinc-600 text-xs">Actualisation auto · 60s</span>
              </div>
              <AlertFeed alerts={alerts} />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
```

**Step 4: Vérifier que le build passe**

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-terminal
npm run build 2>&1 | tail -10
```

Expected: `✓ Compiled successfully`

**Step 5: Commit**

```bash
git add src/app/scanner/page.tsx src/components/AlertFeed.tsx src/components/ScannerConfigPanel.tsx src/lib/api.ts
git commit -m "feat: add scanner page with alert feed and config panel"
```

---

## Task 10 : Navbar — lien vers le scanner

**Files:**
- Modify: `src/app/page.tsx`

**Step 1: Ajouter le lien Scanner dans le header de page.tsx**

Modifier la section `<header>` dans `src/app/page.tsx` — ajouter un import Link et un lien Scanner :

```tsx
// Ajouter en haut du fichier :
import Link from "next/link";

// Modifier le <header> existant :
<header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-4">
  <span className="text-teal-400 font-bold text-lg tracking-tight">WEEFIN</span>
  <span className="text-zinc-600 text-sm">TERMINAL</span>
  <nav className="flex items-center gap-4 ml-4">
    <span className="text-teal-400 text-sm font-medium">Terminal</span>
    <Link href="/scanner" className="text-zinc-500 text-sm hover:text-zinc-300">
      Scanner
    </Link>
  </nav>
  <div className="flex-1 flex justify-center">
    <SearchBar onSelect={handleSelect} />
  </div>
</header>
```

**Step 2: Vérifier que le build passe**

```bash
npm run build 2>&1 | tail -10
```

Expected: `✓ Compiled successfully`

**Step 3: Commit**

```bash
git add src/app/page.tsx
git commit -m "feat: add Scanner nav link in terminal header"
```

---

## Task 11 : Deploy

### 11a — Push backend sur Railway

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-api
git push
```

Railway redéploie automatiquement. Le backend aura les nouveaux endpoints `/scanner/*`.

### 11b — Ajouter Redis sur Railway

1. Aller sur [railway.app](https://railway.app) → ton projet `weefin-api`
2. Cliquer **New** → **Database** → **Add Redis**
3. Railway crée le service Redis et injecte automatiquement `REDIS_URL` dans tous les services du projet

### 11c — Créer le service Celery Worker sur Railway

1. Dans le même projet Railway → **New** → **GitHub Repo** → sélectionner `RobinPaquet/Nexura` (le même repo que weefin-api)
2. Dans les settings du nouveau service → **Settings** → **Deploy** → **Start Command** :
   ```
   .venv/bin/celery -A celery_app worker --beat -l info
   ```
3. Ce service n'a pas besoin de healthcheck ni de PORT — désactiver le healthcheck dans les settings

### 11d — Push frontend sur Vercel

```bash
cd /Users/robin/Desktop/Weefinnn/weefin-terminal
git push
```

Vercel redéploie automatiquement depuis GitHub.

### 11e — Vérifier le déploiement

```bash
# Tester les nouveaux endpoints
curl https://web-production-9cd14.up.railway.app/scanner/alerts
curl https://web-production-9cd14.up.railway.app/scanner/config
```

Expected : `{"alerts":[],"count":0}` et `{"esg_min":0.0,...}`

---

## Résumé des fichiers créés/modifiés

**weefin-api :**
| Fichier | Action |
|---|---|
| `requirements.txt` | + anthropic |
| `celery_app.py` | Nouveau |
| `tasks.py` | Nouveau |
| `models/scanner.py` | Nouveau |
| `services/screener.py` | Nouveau |
| `services/news_scanner.py` | Nouveau |
| `routers/scanner.py` | Nouveau |
| `main.py` | + scanner router + create_scanner_tables |
| `tests/test_celery_app.py` | Nouveau |
| `tests/test_scanner_models.py` | Nouveau |
| `tests/test_screener.py` | Nouveau |
| `tests/test_news_scanner.py` | Nouveau |
| `tests/test_scanner_router.py` | Nouveau |

**weefin-terminal :**
| Fichier | Action |
|---|---|
| `src/lib/api.ts` | + fetchAlerts, fetchScannerConfig, saveScannerConfig |
| `src/app/scanner/page.tsx` | Nouveau |
| `src/components/AlertFeed.tsx` | Nouveau |
| `src/components/ScannerConfigPanel.tsx` | Nouveau |
| `src/app/page.tsx` | + nav link Scanner |
