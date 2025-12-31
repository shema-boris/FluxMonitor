# FluxMonitor — Distributed Price Intelligence System

 [![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#tech-stack)
 [![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688)](#tech-stack)
 [![Celery](https://img.shields.io/badge/Celery-5.4.0-37814A)](#tech-stack)
 [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](#tech-stack)
 [![Redis](https://img.shields.io/badge/Redis-7-DC382D)](#tech-stack)
 [![Playwright](https://img.shields.io/badge/Playwright-Chromium-black)](#tech-stack)
 [![Streamlit](https://img.shields.io/badge/Streamlit-1.37.0-FF4B4B)](#tech-stack)
 [![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)](#getting-started)
 
 **FluxMonitor** is a distributed, asynchronous price intelligence system that scrapes product pages, stores historical prices, and visualizes trends over time.

 ## Features

 - **Track product URLs** via a FastAPI management API (`POST /track`).
 - **Asynchronous scraping** with Celery workers and Redis as broker/backend.
 - **JS-heavy site support** via Playwright (headless Chromium).
 - **Historical price persistence** in PostgreSQL (one Product → many PriceRecords).
 - **Price history query endpoint** (`GET /prices/{product_id}`).
 - **Streamlit dashboard** for interactive trend visualization.
 - **Alembic migrations** for schema management.
 - **Health checks** for API (`/healthz`) and dashboard.
 - **Optional scheduled scraping** scaffold via Celery Beat (Compose profile).

 ## Prerequisites

 - Docker + Docker Compose

 ## Tech Stack

 - **Language**
   - Python 3.10+
 - **API**
   - FastAPI, Uvicorn
 - **Async task processing**
   - Celery, Redis
 - **Scraping**
   - Playwright (Chromium)
 - **Database**
   - PostgreSQL
 - **ORM / Migrations**
   - SQLAlchemy (async), Alembic
 - **Dashboard**
   - Streamlit, Pandas
 - **Containerization**
   - Docker, Docker Compose

 ## Getting Started

 ### 1) Clone

 ```bash
 git clone <your-repo-url>
 cd FluxMonitor
 ```

 ### 3) Build and start the stack

 ```bash
 cd flux_monitor
 docker compose up --build
 ```

 Services:

 - API: `http://localhost:8000`
 - Dashboard: `http://localhost:8501`
 - Postgres: `localhost:5432`
 - Redis: `localhost:6379`

 ### 4) Run migrations

 In another terminal:

 ```bash
 docker compose exec api alembic -c app/migrations/alembic.ini upgrade head
 ```

 ## Usage

 ### API: Track a product

 Endpoint:

 - `POST /track`

 Example (PowerShell-friendly):

 ```powershell
 $body = @{ 
   url = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
   name = "A Light in the Attic"
   price_selector = ".price_color"
 } | ConvertTo-Json

 Invoke-RestMethod -Method Post -Uri "http://localhost:8000/track" -ContentType "application/json" -Body $body
 ```

 Response includes:

 - `product_id`
 - `task_id` (Celery task)

 ### API: Fetch price history

 - `GET /prices/{product_id}`

 ```powershell
 Invoke-RestMethod -Method Get -Uri "http://localhost:8000/prices/1" | ConvertTo-Json -Depth 5
 ```

 ### Dashboard

 Open:

 - `http://localhost:8501`

 ## Operational Notes

 ### Health

 - API health: `GET http://localhost:8000/healthz`
 - Dashboard health: `GET http://localhost:8501/_stcore/health`

 ### Optional scheduled scraping (Celery Beat)

 A Celery Beat service is included behind a Docker Compose profile. Enable it with:

 ```bash
 docker compose --profile beat up -d beat
 ```

 ## License

 This project is licensed under the **[Insert License, e.g., MIT]**.

