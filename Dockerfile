FROM python:3.11-slim
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_HOME="/opt/poetry"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential curl git ca-certificates wget gnupg \
       libpq-dev libffi-dev libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 libgtk-3-0 libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir "poetry>=1.5.0"

WORKDIR /app

# Copy lockfiles first to take advantage of Docker layer caching
COPY pyproject.toml poetry.lock* /app/

# Install dependencies (system env, no virtualenv)
RUN poetry install --no-interaction --no-ansi --no-root --only main || poetry install --no-interaction --no-ansi

# Copy project files
COPY . /app

# Ensure output directory exists
RUN mkdir -p /app/parfumo_dumps

# Add entrypoint
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Also install entrypoint in a stable location that won't be masked by a host mount
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["scrapy", "crawl", "parfumo_spider", "-a", "max_brand_pages=1"]
