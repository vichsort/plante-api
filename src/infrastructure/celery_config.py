import os

from celery import Celery
from celery.schedules import crontab

broker_url = os.getenv("REDIS_ENDPOINT", "redis://localhost:6379/0")
if not broker_url.startswith("redis://"):
    pwd = os.getenv("REDIS_PASSWORD", "")
    host = os.getenv("REDIS_ENDPOINT", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    auth = f":{pwd}@" if pwd else ""
    broker_url = f"redis://{auth}{host}:{port}/0"

celery_app = Celery(
    "plante",
    broker=broker_url,
    backend=broker_url,
)

celery_app.conf.beat_schedule = {
    "anonymize-confirmed-samples-daily": {
        "task": "workers.anonymize_confirmed_samples",
        "schedule": crontab(hour=3, minute=0),
    },
}