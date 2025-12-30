 FROM python:3.10-slim-bookworm

 ENV PYTHONDONTWRITEBYTECODE=1 \
     PYTHONUNBUFFERED=1 \
     PIP_NO_CACHE_DIR=1 \
     PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

 WORKDIR /app

 RUN apt-get update \
     && apt-get install -y --no-install-recommends \
        curl \
     && rm -rf /var/lib/apt/lists/*

 RUN groupadd -g 10001 app \
     && useradd -m -u 10001 -g 10001 -s /bin/bash app

 RUN mkdir -p /ms-playwright \
     && chown -R app:app /ms-playwright

 COPY requirements.txt /app/requirements.txt
 RUN pip install --upgrade pip \
     && pip install -r /app/requirements.txt \
     && python -m playwright install --with-deps chromium \
     && chown -R app:app /ms-playwright

 COPY app /app/app

 USER app

 EXPOSE 8000
 EXPOSE 8501

