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
