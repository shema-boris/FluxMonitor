from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.core.db import async_session_maker
from app.core.celery_app import celery_app
from app.models.product import Product
from app.tasks.scrape import scrape_product


logger = logging.getLogger(__name__)


async def _get_all_product_ids() -> list[int]:
    async with async_session_maker() as session:
        ids = await session.scalars(select(Product.id).order_by(Product.id.asc()))
        return list(ids.all())


@celery_app.task(bind=True, name="flux_monitor.scrape_all_products")
def scrape_all_products(self) -> dict:
    product_ids = asyncio.run(_get_all_product_ids())

    dispatched = 0
    for pid in product_ids:
        scrape_product.delay(pid)
        dispatched += 1

    logger.info("scrape_all_dispatched task_id=%s count=%s", getattr(self.request, "id", None), dispatched)
    return {"dispatched": dispatched}
