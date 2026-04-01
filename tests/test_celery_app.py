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
