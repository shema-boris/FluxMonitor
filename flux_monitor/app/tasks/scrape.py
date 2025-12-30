from __future__ import annotations

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from celery import Task
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.db import async_session_maker
from app.models.price_record import PriceRecord
from app.models.product import Product


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedPrice:
    amount: Decimal
    currency: str


_CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
}


def _normalize_number(raw: str) -> Decimal:
    s = raw.strip()
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[^0-9,\.]", "", s)

    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")

    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"Failed to parse numeric value from '{raw}' -> '{s}'") from exc


def parse_price(text: str) -> ParsedPrice:
    if not text or not text.strip():
        raise ValueError("Empty price text")

    currency = "USD"
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in text:
            currency = code
            break

    m = re.search(r"([0-9][0-9\.,\s\u00a0]*)", text)
    if not m:
        raise ValueError(f"No numeric value found in '{text}'")

    amount = _normalize_number(m.group(1))
    return ParsedPrice(amount=amount, currency=currency)


async def _extract_price_text(page, selector_override: str | None) -> str:
    selectors: list[str] = []
    if selector_override:
        selectors.append(selector_override)

    selectors.extend(
        [
            '[itemprop="price"]',
            'meta[property="product:price:amount"]',
            'meta[name="product:price:amount"]',
            '[data-test*="price" i]',
            '[class*="price" i]',
        ]
    )

    for selector in selectors:
        try:
            if selector.startswith("meta"):
                value = await page.locator(selector).first.get_attribute("content")
                if value:
                    return value

            text = await page.locator(selector).first.inner_text(timeout=1500)
            if text and text.strip():
                return text
        except Exception:
            continue

    body_text = await page.locator("body").inner_text(timeout=2000)
    for pattern in [
        r"\$\s?[0-9][0-9\.,]*",
        r"€\s?[0-9][0-9\.,]*",
        r"£\s?[0-9][0-9\.,]*",
    ]:
        m = re.search(pattern, body_text)
        if m:
            return m.group(0)

    raise ValueError("Unable to locate price on page")


async def _scrape_and_persist(product_id: int, user_agent: str, politeness_delay_s: tuple[float, float]) -> ParsedPrice:
    async with async_session_maker() as session:
        product = await session.scalar(select(Product).where(Product.id == product_id))
        if not product:
            raise ValueError(f"Product not found: {product_id}")

        delay = random.uniform(*politeness_delay_s)
        await asyncio.sleep(delay)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=user_agent)
            page = await context.new_page()

            try:
                await page.goto(product.url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(500)
                price_text = await _extract_price_text(page, product.price_selector)
            finally:
                await context.close()
                await browser.close()

        parsed = parse_price(price_text)

        session.add(
            PriceRecord(
                product_id=product.id,
                price=parsed.amount,
                currency=parsed.currency,
            )
        )
        await session.commit()

        return parsed


class FluxTask(Task):
    autoretry_for = ()


@celery_app.task(bind=True, base=FluxTask, name="flux_monitor.scrape_product")
def scrape_product(self: FluxTask, product_id: int) -> dict:
    task_id = getattr(self.request, "id", None)

    logger.info("scrape_start task_id=%s product_id=%s", task_id, product_id)

    try:
        parsed = asyncio.run(
            _scrape_and_persist(
                product_id=product_id,
                user_agent="FluxMonitor/1.0 (+https://example.local)",
                politeness_delay_s=(0.5, 2.0),
            )
        )
    except PlaywrightTimeoutError as exc:
        retries = int(getattr(self.request, "retries", 0))
        countdown = min(300, 5 * (2**retries)) + random.randint(0, 3)
        logger.warning(
            "scrape_retry_timeout task_id=%s product_id=%s retries=%s countdown=%s err=%s",
            task_id,
            product_id,
            retries,
            countdown,
            str(exc),
        )
        raise self.retry(exc=exc, countdown=countdown, max_retries=5)
    except Exception as exc:
        retries = int(getattr(self.request, "retries", 0))
        if retries >= 5:
            logger.error(
                "scrape_failed task_id=%s product_id=%s retries=%s err=%s",
                task_id,
                product_id,
                retries,
                str(exc),
            )
            raise

        countdown = min(300, 5 * (2**retries)) + random.randint(0, 3)
        logger.warning(
            "scrape_retry task_id=%s product_id=%s retries=%s countdown=%s err=%s",
            task_id,
            product_id,
            retries,
            countdown,
            str(exc),
        )
        raise self.retry(exc=exc, countdown=countdown, max_retries=5)

    logger.info(
        "scrape_success task_id=%s product_id=%s amount=%s currency=%s",
        task_id,
        product_id,
        str(parsed.amount),
        parsed.currency,
    )
    return {"product_id": product_id, "price": str(parsed.amount), "currency": parsed.currency}
