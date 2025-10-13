# Copilot Instructions for the_perfume_parser

## Project Overview
Professional Scrapy-based web scraping system for extracting perfume data from Parfumo.com. Implements Scrapy best practices including ItemLoaders, Feed Exports, comprehensive pipelines, and Playwright integration for JavaScript-rendered content.

## Core Architecture

### Project Structure
```
perfume_scraper/
├── spiders/
│   ├── parfumo_spider.py          # Brand discovery & pagination (BrandItem, BrandPageItem)
│   └── parfumo_perfume_spider.py  # Detailed perfume scraping (PerfumeItem)
├── items.py                        # Structured data models (scrapy.Item)
├── loaders.py                      # ItemLoaders with input/output processors
├── pipelines.py                    # Data validation, cleaning, deduplication, export
├── middlewares.py                  # User-agent rotation, delays, proxy support
└── settings.py                     # Global Scrapy configuration

Output:
├── parfumo_dumps/                  # Main output directory (gitignored)
│   ├── brands_TIMESTAMP.json       # Feed Export: All brands
│   ├── brands_TIMESTAMP.csv        # Feed Export: All brands
│   ├── brand_pages_TIMESTAMP.json  # Feed Export: Brand pagination data
│   ├── brand_pages/BRAND/          # Debug HTML dumps
│   └── perfumes/BRAND_NAME.json    # Individual perfume exports
└── httpcache/                      # HTTP cache (24h TTL, gitignored)
```

## Scrapy Best Practices Implementation

### 1. Items & ItemLoaders
**Always use ItemLoaders for data extraction:**
```python
from perfume_scraper.items import BrandItem
from perfume_scraper.loaders import BrandItemLoader

loader = BrandItemLoader(item=BrandItem(), selector=selector)
loader.add_css('name', '::text')
loader.add_css('url', '::attr(href)')
loader.add_value('slug', brand_url)  # Computed field
item = loader.load_item()
```

**Benefits:**
- Separation of extraction logic from parsing logic
- Input/output processors handle cleaning automatically
- Type-safe field access via `ItemAdapter`

**Custom Processors:**
- `clean_text()` - Strip whitespace, normalize spaces
- `normalize_brand_name()` - Clean brand names
- `extract_slug_from_url()` - Parse URL components
- `clean_number()` - Extract integers from text

### 2. Feed Exports
**Use Feed Exports for bulk data output (NOT custom JSON writing):**
```python
# In settings.py - Automatic output with format, filtering, and type separation
FEEDS = {
    'parfumo_dumps/brands_%(time)s.json': {
        'format': 'json',
        'indent': 2,
        'item_classes': ['perfume_scraper.items.BrandItem'],
    },
}
```

**Advantages:**
- Automatic timestamping via `%(time)s`
- Multiple formats simultaneously (JSON, CSV, XML)
- Item type filtering via `item_classes`
- No manual file handling in spider code

### 3. Pipeline Architecture
**Ordered processing chain (100-900 priority range):**
1. **ValidationPipeline (300)**: Required field validation per item type
2. **DataCleaningPipeline (400)**: Normalize strings, URLs, slugs
3. **DuplicatesPipeline (500)**: In-memory deduplication by identifier
4. **PerfumeJsonExportPipeline (600)**: Individual file exports (perfumes only)
5. **StatisticsPipeline (800)**: Collect processing metrics

**Pipeline Pattern:**
```python
def process_item(self, item, spider):
    adapter = ItemAdapter(item)
    item_type = type(item).__name__
    
    # Type-specific logic
    if item_type == 'BrandItem':
        # Validate/clean/process
        pass
    
    return item  # Always return item to next pipeline
```

### 4. Settings Configuration

**Anti-Detection Settings:**
```python
ROBOTSTXT_OBEY = True                    # Respect site rules
DOWNLOAD_DELAY = 3                       # 3s between requests
RANDOMIZE_DOWNLOAD_DELAY = True          # 50-150% variance
CONCURRENT_REQUESTS = 1                  # Sequential requests only
AUTOTHROTTLE_ENABLED = True              # Dynamic throttling
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5    # Conservative
```

**Retry & Error Handling:**
```python
RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]
DOWNLOAD_TIMEOUT = 60
```

**Caching:**
```python
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24 hours
HTTPCACHE_DIR = 'httpcache'
```

**Headers (realistic browser simulation):**
```python
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,...',
    'Accept-Language': 'en-US,en;q=0.9',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    # ... full browser headers
}
```

### 5. Middleware Best Practices

**User-Agent Rotation:**
```python
# PerfumeScraperDownloaderMiddleware
user_agent = self.user_agent_rotator.get_random_user_agent()
request.headers['User-Agent'] = user_agent
time.sleep(random.uniform(0.5, 2.0))  # Random delay
```

**Proxy Support (ready for activation):**
```python
# ProxyRotationMiddleware - Add proxies when needed
self.proxies = [
    # 'http://proxy1:port',
]
```

### 6. Playwright Integration

**Configuration:**
```python
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
PLAYWRIGHT_BROWSER_TYPE = 'chromium'
PLAYWRIGHT_LAUNCH_OPTIONS = {'headless': True, 'timeout': 60000}
```

**Request Pattern:**
```python
yield scrapy.Request(
    url=url,
    callback=self.parse_perfume,
    meta={
        "playwright": True,
        "playwright_include_page": True,
        "playwright_page_goto_kwargs": {
            "wait_until": "networkidle",
            "timeout": 30000,
        },
    },
)
```

**Async Parsing:**
```python
async def parse_perfume(self, response):
    page = response.meta.get("playwright_page")
    
    # Wait for AJAX content
    await page.wait_for_timeout(2000)
    
    # Extract dynamic data
    chart_html = await classification_holder.first.inner_html()
    
    # Always clean up
    # (Playwright handler auto-closes page)
```

## Spider Development Patterns

### Brand Discovery Spider (parfumo_spider.py)
**Purpose:** Walk A-Z letter pages → Extract brands → Follow pagination

**Key Features:**
- 27 start URLs (0, a-z)
- `seen_brands` set for deduplication
- `max_brand_pages` parameter (0 = unlimited)
- Yields `BrandItem` + `BrandPageItem`
- Uses `urljoin()` for relative URLs
- Saves debug HTML per brand

**Pagination Handling:**
```python
def _get_next_page_url(self, response):
    next_link = response.css('a[rel="next"].paging_links::attr(href)').get()
    return urljoin(response.url, next_link) if next_link else None
```

### Perfume Detail Spider (parfumo_perfume_spider.py)
**Purpose:** Extract full perfume data including Charts (Playwright)

**Data Extracted:**
- Name, brand, description, gender
- Perfumer info
- Main accords (with intensity)
- Fragrance pyramid (top/heart/base notes)
- Ratings (scent, longevity, sillage, bottle, overall)
- Charts classification (type, style, season, occasion)

**Charts Extraction Pattern:**
```python
async def extract_charts_data(self, response):
    page = response.meta.get("playwright_page")
    
    # Locate Charts section
    charts_heading = page.locator('h2:has-text("Charts")')
    await charts_heading.first.scroll_into_view_if_needed()
    
    # Wait for AJAX load
    classification_holder = page.locator('#classification_holder_am')
    for attempt in range(10):
        html = await classification_holder.first.inner_html()
        if "ajax_loader" not in html:
            break
        await page.wait_for_timeout(1000)
    
    # Parse extracted HTML
    return self._parse_chart_html(html)
```

## Command Reference

### Running Spiders
```bash
# Brand discovery (unlimited)
poetry run scrapy crawl parfumo_spider

# Brand discovery (limited to 10 brands)
poetry run scrapy crawl parfumo_spider -a max_brand_pages=10

# Perfume details (single URL)
poetry run scrapy crawl parfumo_perfume_spider -a url="https://www.parfumo.com/Perfumes/..."

# Perfume details (batch from file)
poetry run scrapy crawl parfumo_perfume_spider -a urls_file="perfume_urls.txt"
```

### Environment Setup
```bash
# Install dependencies
poetry install

# Install Playwright browsers
poetry run playwright install chromium
```

## Anti-Blocking Strategy

**Current Implementations:**
1. ✅ `robots.txt` compliance
2. ✅ Download delays (3s + randomization)
3. ✅ AutoThrottle (adaptive delays)
4. ✅ User-Agent rotation (Chrome/Firefox/Safari)
5. ✅ Realistic browser headers
6. ✅ Cookie persistence
7. ✅ HTTP caching (24h)
8. ✅ Retry mechanism (5 attempts)

**Potential Additions:**
- Proxy rotation (middleware ready)
- Session persistence (cookies enabled)
- Referer header management
- Accept-Language rotation

## Development Guidelines

### Adding New Item Types
1. Define in `items.py` (inherit `scrapy.Item`)
2. Create ItemLoader in `loaders.py` with processors
3. Add validation rules to `ValidationPipeline.REQUIRED_FIELDS`
4. Update `DuplicatesPipeline` with identifier logic
5. Add Feed Export configuration in `settings.py`

### Adding New Spiders
1. Inherit from `scrapy.Spider`
2. Define `name`, `allowed_domains`, `start_urls`
3. Use ItemLoaders for extraction
4. Implement `errback` for error handling
5. Use `urljoin()` for URL construction
6. Add `closed()` method for statistics

### Debugging
- Check `parfumo_dumps/brand_pages/*/` for HTML dumps
- Enable `LOG_LEVEL = 'DEBUG'` in settings
- Use `AUTOTHROTTLE_DEBUG = True` for throttle stats
- Review `httpcache/` for cached responses

## Critical Rules
1. **Never** write custom JSON export code - use Feed Exports
2. **Always** use ItemLoaders for data extraction
3. **Always** implement `errback` for requests
4. **Never** store items in spider attributes (memory leak)
5. **Always** use `urljoin()` for relative URLs
6. **Never** block the reactor - use `await` for Playwright
7. **Always** validate with `ItemAdapter` in pipelines
8. **Never** modify `response` object in pipelines

---
_Last Updated: 2025-10-13 | Scrapy 2.13.3 | Python 3.11_
