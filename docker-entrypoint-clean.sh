#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/parfumo_dumps
chown -R "$(id -u)":"$(id -g)" /app/parfumo_dumps || true

if [ "${INSTALL_PLAYWRIGHT_BROWSERS:-0}" = "1" ]; then
  echo "Installing Playwright browsers..."
  python -m pip install --no-cache-dir playwright || true
  python -m playwright install --with-deps chromium || true
fi

if [ $# -eq 0 ]; then
  if command -v scrapy >/dev/null 2>&1; then
    exec scrapy crawl parfumo_spider -a max_brand_pages=0
  else
    echo "scrapy not found in PATH" >&2
    exit 1
  fi
else
  exec "$@"
fi
