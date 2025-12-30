from __future__ import annotations

import logging

import anyio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PriceHistoryResponse, PricePoint, TrackRequest, TrackResponse
from app.core.db import get_session
from app.models.price_record import PriceRecord
from app.models.product import Product
from app.tasks.scrape import scrape_product


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.post("/track", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
async def track_product(payload: TrackRequest, session: AsyncSession = Depends(get_session)) -> TrackResponse:
    product = Product(name=payload.name, url=str(payload.url), price_selector=payload.price_selector)
    session.add(product)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(Product).where(Product.url == str(payload.url)))
        if not existing:
            raise HTTPException(status_code=500, detail="Failed to create or fetch product")
        product = existing
    else:
        await session.refresh(product)

    def _dispatch() -> str | None:
        result = scrape_product.delay(product.id)
        return result.id

    task_id = await anyio.to_thread.run_sync(_dispatch)

    logger.info("track_created product_id=%s task_id=%s url=%s", product.id, task_id, product.url)

    return TrackResponse(product_id=product.id, task_id=task_id)


@router.get("/prices/{product_id}", response_model=PriceHistoryResponse)
async def get_prices(product_id: int, session: AsyncSession = Depends(get_session)) -> PriceHistoryResponse:
    product = await session.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    rows = await session.scalars(
        select(PriceRecord).where(PriceRecord.product_id == product_id).order_by(PriceRecord.timestamp.asc())
    )

    prices = [
        PricePoint(price=row.price, currency=row.currency, timestamp=row.timestamp)
        for row in rows.all()
    ]

    return PriceHistoryResponse(product_id=product_id, prices=prices)
