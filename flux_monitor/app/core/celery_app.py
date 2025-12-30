from __future__ import annotations

import logging

from celery import Celery

from app.core.settings import settings


logger = logging.getLogger(__name__)

broker_url = settings.celery_broker_url or settings.redis_url
result_backend = settings.celery_result_backend or settings.redis_url

celery_app = Celery(
    "flux_monitor",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks.scrape", "app.tasks.schedule"],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
    beat_schedule={
        "scrape-all-products-hourly": {
            "task": "flux_monitor.scrape_all_products",
            "schedule": 3600.0,
        }
    },
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
