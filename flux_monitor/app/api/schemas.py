from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, HttpUrl


class TrackRequest(BaseModel):
    url: HttpUrl
    name: str | None = None
    price_selector: str | None = None


class TrackResponse(BaseModel):
    product_id: int
    task_id: str | None


class PricePoint(BaseModel):
    price: Decimal
    currency: str
    timestamp: datetime


class PriceHistoryResponse(BaseModel):
    product_id: int
    prices: list[PricePoint]
