# Scrapy settings for perfume_scraper project

BOT_NAME = 'perfume_scraper'

LOG_LEVEL = 'DEBUG'
AUTOTHROTTLE_DEBUG = True

SPIDER_MODULES = ['perfume_scraper.spiders']
NEWSPIDER_MODULE = 'perfume_scraper.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure delays for requests
DOWNLOAD_DELAY = 3  # Increased delay between requests
RANDOMIZE_DOWNLOAD_DELAY = True  # Randomize delay (50-150% of DOWNLOAD_DELAY)

# Configure concurrent requests
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
CONCURRENT_REQUESTS_PER_IP = 1

# Enable autothrottling
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 60  # Max 60 seconds if server is slow
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5  # Very conservative
AUTOTHROTTLE_DEBUG = False

# Configure user agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'

# Cookie and session handling
COOKIES_ENABLED = True
COOKIES_DEBUG = False

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 5  # Retry up to 5 times
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]  # Added 403 Forbidden
RETRY_PRIORITY_ADJUST = -1

# Download timeout
DOWNLOAD_TIMEOUT = 60  # 60 seconds timeout

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # Cache for 24 hours
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# Redirect settings
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 3

# HTTP compression
COMPRESSION_ENABLED = True

# Telnet console disabled for production
TELNETCONSOLE_ENABLED = False

# Logging
LOG_LEVEL = 'INFO'
LOG_ENABLED = True

# Depth limit (not needed for this spider but good practice)
DEPTH_LIMIT = 2

# Default request headers (will be merged with custom headers)
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

# Feed Exports - Automatic output to multiple formats
FEEDS = {
    'parfumo_dumps/brands_%(time)s.json': {
        'format': 'json',
        'encoding': 'utf-8',
        'indent': 2,
        'store_empty': False,
        'overwrite': False,
        'fields': ['name', 'url', 'slug', 'letter_category', 'source_url', 'scraped_at', 'scraped_by'],
        'item_classes': ['perfume_scraper.items.BrandItem'],
    },
    'parfumo_dumps/brands_%(time)s.csv': {
        'format': 'csv',
        'encoding': 'utf-8',
        'store_empty': False,
        'overwrite': False,
        'fields': ['name', 'url', 'slug', 'letter_category', 'scraped_at'],
        'item_classes': ['perfume_scraper.items.BrandItem'],
    },
    'parfumo_dumps/brand_pages_%(time)s.json': {
        'format': 'json',
        'encoding': 'utf-8',
        'indent': 2,
        'store_empty': False,
        'overwrite': False,
        'fields': ['brand_name', 'brand_url', 'perfume_urls', 'total_perfumes', 'pages_scraped', 'scraped_at', 'scraped_by', 'country', 'established'],
        'item_classes': ['perfume_scraper.items.BrandPageItem'],
    },
}

# Item Pipelines - Process items through validation, cleaning, and export
ITEM_PIPELINES = {
    'perfume_scraper.pipelines.ValidationPipeline': 300,
    'perfume_scraper.pipelines.DataCleaningPipeline': 400,
    'perfume_scraper.pipelines.DuplicatesPipeline': 500,
    'perfume_scraper.pipelines.StatisticsPipeline': 800,
}

# Playwright integration and async reactor
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}



TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = 'chromium'
PLAYWRIGHT_LAUNCH_OPTIONS = {
    'headless': True,
    'timeout': 60000,
}