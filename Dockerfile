FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential curl git ca-certificates wget gnupg \
       libpq-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry>=1.5.0"

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

RUN poetry install --no-interaction --no-ansi --no-root --only main || poetry install --no-interaction --no-ansi

COPY . /app

RUN mkdir -p /app/parfumo_dumps

COPY docker-entrypoint-clean.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

COPY docker-entrypoint-clean.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["scrapy", "crawl", "parfumo_spider", "-a", "max_brand_pages=1"]
