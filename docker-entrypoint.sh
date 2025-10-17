#!/usr/bin/env bash
set -euo pipefail

# Default command passed into container
CMD_CMD=("$@")

# Ensure output directory exists and is writable
mkdir -p /app/parfumo_dumps
chown -R $(id -u):$(id -g) /app/parfumo_dumps || true

# Optionally install Playwright browsers if requested
if [ "${INSTALL_PLAYWRIGHT_BROWSERS:-0}" = "1" ]; then
  echo "Installing Playwright browsers..."
  # Install Playwright and browsers via playwright CLI if available
  python -m pip install --no-cache-dir playwright
  python -m playwright install --with-deps chromium
fi

if [ ${#CMD_CMD[@]} -eq 0 ]; then
  # Default behaviour if no command provided
  exec scrapy crawl parfumo_spider -a max_brand_pages=1
else
  #!/usr/bin/env bash
  set -euo pipefail

  # Default command passed into container
  CMD_CMD=("$@")

  # Ensure output directory exists and is writable
  mkdir -p /app/parfumo_dumps
  chown -R $(id -u):$(id -g) /app/parfumo_dumps || true

  # Optionally install Playwright browsers if requested
  if [ "${INSTALL_PLAYWRIGHT_BROWSERS:-0}" = "1" ]; then
    echo "Installing Playwright browsers..."
    # Install Playwright and browsers via playwright CLI if available
    python -m pip install --no-cache-dir playwright
    python -m playwright install --with-deps chromium
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
