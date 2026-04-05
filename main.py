from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from apscheduler.schedulers.background import BackgroundScheduler
    from services.screener import run_screener
    from services.news_scanner import fetch_esg_news

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_screener, "interval", minutes=15, id="screener")
    scheduler.add_job(
        lambda: asyncio.run(fetch_esg_news()), "interval", hours=1, id="news"
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Weefin API", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_origin_regex=r"https://.*\.vercel\.app",
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

from routers.backtest import router as backtest_router
app.include_router(backtest_router)

from models.scanner import create_scanner_tables as create_scanner_tables_fn
create_scanner_tables_fn()


@app.get("/health")
async def health():
    return {"status": "ok", "version": VERSION}
