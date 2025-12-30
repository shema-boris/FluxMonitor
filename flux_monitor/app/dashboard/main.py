from __future__ import annotations

import os
import time
from urllib.parse import urlparse

import pandas as pd
import sqlalchemy as sa
import streamlit as st


def _sync_db_url_from_env() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "fluxmonitor")
        user = os.getenv("POSTGRES_USER", "fluxmonitor")
        password = os.getenv("POSTGRES_PASSWORD", "fluxmonitor")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

    parsed = urlparse(url)
    scheme = parsed.scheme

    if scheme.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    elif scheme == "postgresql":
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    return url


@st.cache_resource
def get_engine() -> sa.Engine:
    return sa.create_engine(_sync_db_url_from_env(), pool_pre_ping=True)


def _rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def main() -> None:
    st.set_page_config(page_title="FluxMonitor Dashboard", layout="wide")
    st.title("FluxMonitor — Price Trends")

    auto_refresh = st.toggle("Auto-refresh", value=False)
    refresh_seconds = st.number_input("Refresh interval (seconds)", min_value=5, max_value=3600, value=30)

    engine = get_engine()

    products = pd.read_sql(
        sa.text("SELECT id, COALESCE(name, url) AS label, url FROM products ORDER BY created_at DESC"),
        con=engine,
    )

    if products.empty:
        st.info("No products tracked yet. Use the API POST /track to add a product.")
        if auto_refresh:
            time.sleep(float(refresh_seconds))
            _rerun()
        return

    selected_label = st.selectbox("Product", options=products["label"].tolist())
    selected = products.loc[products["label"] == selected_label].iloc[0]
    product_id = int(selected["id"])

    st.caption(f"Product ID: {product_id}")
    st.caption(f"URL: {selected['url']}")

    prices = pd.read_sql(
        sa.text(
            "SELECT timestamp, price, currency FROM price_records WHERE product_id = :pid ORDER BY timestamp ASC"
        ),
        con=engine,
        params={"pid": product_id},
    )

    if prices.empty:
        st.warning("No price records yet for this product. The worker may still be scraping.")
    else:
        prices["timestamp"] = pd.to_datetime(prices["timestamp"], utc=True)
        st.line_chart(prices.set_index("timestamp")["price"], height=420)
        st.dataframe(prices, use_container_width=True)

    if auto_refresh:
        time.sleep(float(refresh_seconds))
        _rerun()


if __name__ == "__main__":
    main()
