#!/usr/bin/env bash
set -euo pipefail

# docker-entrypoint-clean.sh - ensures output dir exists and runs the requested command
# If INSTALL_PLAYWRIGHT_BROWSERS=1 is set, install Playwright browsers first.

# Capture command args
CMD_CMD=("$@")

# Ensure output directory exists and is writable
mkdir -p /app/parfumo_dumps
chown -R "$(id -u)":"$(id -g)" /app/parfumo_dumps || true

# Optionally install Playwright browsers if requested
if [ "${INSTALL_PLAYWRIGHT_BROWSERS:-0}" = "1" ]; then
  echo "Installing Playwright browsers..."
  python -m pip install --no-cache-dir playwright || true
  python -m playwright install --with-deps chromium || true
fi

if [ ${#CMD_CMD[@]} -eq 0 ]; then
  # Default behaviour if no command provided
  if command -v scrapy >/dev/null 2>&1; then
    exec scrapy crawl parfumo_spider -a max_brand_pages=1
  else
    echo "scrapy not found in PATH" >&2
    exit 1
  fi
else
  exec "$@"
fi
