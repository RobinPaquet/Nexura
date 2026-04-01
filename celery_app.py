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
