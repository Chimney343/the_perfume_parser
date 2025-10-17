# Docker support for the_perfume_parser

This repository includes a Dockerfile and docker-compose configuration to run the Parfumo spiders inside a container and persist outputs to the host `parfumo_dumps` directory.

Build image:

```powershell
docker build -t parfumo_scraper:latest .
```

Run with docker (bind-mounts outputs to host):

```powershell
docker run --rm -v ${PWD}:/app -v ${PWD}\parfumo_dumps:/app/parfumo_dumps parfumo_scraper:latest
```

Run using docker-compose (recommended):

```powershell
docker-compose up --build
```

Notes:
- The Docker image installs dependencies via Poetry. If you need Playwright browsers for JS rendering, set environment variable `INSTALL_PLAYWRIGHT_BROWSERS=1` when running the container. This will install Playwright and Chromium before running the spider.
- The container's default command runs `parfumo_spider` with `-a max_brand_pages=1`. Override the command to run different spiders or limits.
