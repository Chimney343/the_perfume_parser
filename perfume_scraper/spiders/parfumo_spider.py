"""
Parfumo spider for scraping ALL brand data from parfumo.com.
This spider walks through all letter pages (0, A-Z) to collect all brands.
Refactored to only handle brand discovery - use parfumo_perfume_spider for perfume details.
"""

import scrapy
import os
import json
from datetime import datetime
import re
from urllib.parse import urljoin
import string
from typing import Dict, List, Set, Any, Optional, Generator, Union
from scrapy.exceptions import NotConfigured

# Import Items and Loaders
from perfume_scraper.items import BrandItem, BrandPageItem
from perfume_scraper.loaders import BrandItemLoader, BrandPageItemLoader


class ParfumoSpider(scrapy.Spider):
    name = 'parfumo_spider'
    allowed_domains = ['parfumo.com']
    
    # Constants for URL filtering and configuration
    MIN_PERFUME_URL_DEPTH = 4  # Minimum slashes to identify perfume detail pages
    DEFAULT_MAX_BRAND_PAGES = 0  # Default limit for brand pages to visit (0 = unlimited)
    
    # Start with all letter pages (0 for numbers, a-z for letters)
    start_urls = [
        'https://www.parfumo.com/Brands/0',  # Numbers
    ] + [f'https://www.parfumo.com/Brands/{letter}' for letter in string.ascii_lowercase]
    
    def __init__(self, *args, **kwargs) -> None:
        super(ParfumoSpider, self).__init__(*args, **kwargs)
        self.timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir: str = "parfumo_dumps"
        
        # Use set for duplicate tracking instead of dictionary
        self.seen_brands: Set[str] = set()
        
        # Counter for brand pages visited
        self.brand_pages_visited: int = 0
        
        # Dictionary to store brand page data during pagination
        # Key: brand_url, Value: dict with perfume_urls set and metadata
        self.brand_page_data: Dict[str, Dict[str, Any]] = {}
        
        # Parameter to limit brand pages to visit (0 = unlimited)
        max_brand_pages_param = kwargs.get('max_brand_pages', self.DEFAULT_MAX_BRAND_PAGES)
        try:
            self.max_brand_pages = int(max_brand_pages_param)
            if self.max_brand_pages < 0:
                self.logger.warning(f"max_brand_pages cannot be negative, using default: {self.DEFAULT_MAX_BRAND_PAGES}")
                self.max_brand_pages = self.DEFAULT_MAX_BRAND_PAGES
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid max_brand_pages value '{max_brand_pages_param}', using default: {self.DEFAULT_MAX_BRAND_PAGES}")
            self.max_brand_pages = self.DEFAULT_MAX_BRAND_PAGES  # Default: visit 1 brand page
        
        # Parameter to control HTML dumping (default: True)
        dump_html_param = kwargs.get('dump_html', 'True')
        self.dump_html = str(dump_html_param).lower() in ('true', '1', 'yes')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Will scrape {len(self.start_urls)} letter pages")
        self.logger.info(f"Max brand pages to visit: {self.max_brand_pages if self.max_brand_pages > 0 else 'unlimited'}")
        self.logger.info(f"HTML dumping: {'enabled' if self.dump_html else 'disabled'}")
    
    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial requests with proper meta information and realistic timing."""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    'dont_cache': False,  # Use cache if available
                    'download_timeout': 60,
                    'max_retry_times': 5,
                },
                errback=self.handle_error,
                dont_filter=False,  # Enable duplicate filtering
            )
    
    def parse(self, response: scrapy.http.Response) -> Generator[Any, None, None]:
        """
        Parse each letter page and extract all brand information.
        
        Args:
            response: Scrapy response object for a letter page
            
        Yields:
            BrandItem: Structured brand data
        """
        # Get the current letter from URL
        current_letter = response.url.split('/')[-1].upper()
        
        self.logger.info(f"Processing letter page: {current_letter}")
        self.logger.debug(f"Response status: {response.status}")
        
        # Extract all brand links from the brands list
        brand_selectors = response.css('div.brands_list a[href*="/Perfumes/"]')
        
        self.logger.info(f"Found {len(brand_selectors)} brands on letter '{current_letter}' page")
        
        # Extract brand information using ItemLoader
        for selector in brand_selectors:
            # Create ItemLoader for this brand
            loader = BrandItemLoader(item=BrandItem(), selector=selector)
            
            # Extract core fields
            loader.add_css('name', '::text')
            loader.add_css('url', '::attr(href)')
            
            # Add derived field - slug from URL
            brand_url = selector.css('::attr(href)').get()
            if brand_url:
                full_url = urljoin(response.url, brand_url)
                loader.add_value('url', full_url)
                loader.add_value('slug', brand_url)
            
            # Add metadata
            loader.add_value('letter_category', current_letter)
            loader.add_value('source_url', response.url)
            loader.add_value('scraped_at', datetime.utcnow().isoformat())
            loader.add_value('scraped_by', self.name)
            
            # Load the item
            item = loader.load_item()
            
            # Check for duplicates
            brand_name = item.get('name')
            if brand_name and brand_name not in self.seen_brands:
                self.seen_brands.add(brand_name)
                yield item
                
                # Follow brand URL if we haven't reached the limit
                if self.max_brand_pages == 0 or self.brand_pages_visited < self.max_brand_pages:
                    brand_url = item.get('url')
                    if brand_url:
                        self.logger.info(f"Following brand page: {brand_name} -> {brand_url}")
                        yield scrapy.Request(
                            url=brand_url,
                            callback=self.parse_brand_page,
                            meta={
                                'brand_name': brand_name,
                                'brand_slug': item.get('slug'),
                                'country': None,  # Will be extracted on first page
                                'established': None,  # Will be extracted on first page
                                'dont_cache': False,
                            },
                            errback=self.handle_error,
                        )
            else:
                self.logger.debug(f"Duplicate brand found: {brand_name}")
        
        # Update stats
        self.crawler.stats.set_value('brands_collected', len(self.seen_brands))
        self.logger.info(f"Total unique brands collected so far: {len(self.seen_brands)}")

    
    def parse_brand_page(self, response: scrapy.http.Response) -> Generator[Any, None, None]:
        """
        Parse a brand's page to extract perfume links, country of origin, and handle pagination.
        
        Pagination structure from HTML:
        - Page numbers: div.paging div.numbers div > a (current has class 'active')
        - Next link: a[rel="next"].paging_links
        - Counter text: div.paging_nrs_cnt (e.g., "1 - 20 by 78")
        
        Args:
            response: Scrapy response object for a brand's page
            
        Yields:
            BrandPageItem: When all pages have been scraped for a brand
            scrapy.Request: For pagination (next page)
        """
        brand_name = response.meta.get('brand_name', 'Unknown')
        brand_slug = response.meta.get('brand_slug', 'unknown')

        # Get current page number from URL or meta (default: 1)
        current_page = int(response.meta.get('current_page', 1))

        # Extract country and established ONLY on first page
        if current_page == 1:
            country = response.css('span.label_a img.flag::attr(alt)').get(default='Unknown')
            established = response.css('span.label_a::text').re_first(r'since (\d{4})')
            # Extract brand description
            description = response.css('div.leading-7.mt-1::text').getall()
            description = ' '.join([text.strip() for text in description if text.strip()])
        else:
            # Reuse from metadata on subsequent pages
            country = response.meta.get('country', 'Unknown')
            established = response.meta.get('established', 'Unknown')
            description = response.meta.get('description', 'Unknown')

        # Initialize brand data if this is the first page
        # Normalize brand URL base (remove query params and trailing slash)
        brand_url_base = response.url.split('?')[0].rstrip('/')  # Remove query params
        if brand_url_base not in self.brand_page_data:
            self.brand_pages_visited += 1
            self.brand_page_data[brand_url_base] = {
                'brand_name': brand_name,
                'brand_url': brand_url_base,
                'perfume_urls': set(),  # Use set for O(1) lookups
                'pages_scraped': 0,
            }
            self.logger.info("=" * 80)
            self.logger.info(f"BRAND PAGE #{self.brand_pages_visited}: {brand_name}")
            self.logger.info(f"URL: {brand_url_base}")
            self.logger.info("=" * 80)
        
        # Get reference to brand data
        brand_data = self.brand_page_data[brand_url_base]
        brand_data['pages_scraped'] += 1
        
        # Update brand data with country and established year
        brand_data['country'] = country
        brand_data['established'] = established
        brand_data['description'] = description
        
        self.logger.info(f"Processing page {current_page} for brand: {brand_name}")
        
        # Save the HTML for first page only (for debugging, if enabled)
        if current_page == 1 and self.dump_html:
            # Create a 'brand_pages' folder inside the output directory
            brand_pages_dir = os.path.join(self.output_dir, "brand_pages")
            os.makedirs(brand_pages_dir, exist_ok=True)

            # Create a folder for the brand inside 'brand_pages'
            # Sanitize brand_slug so it is safe for filesystem paths
            safe_slug = re.sub(r'[^A-Za-z0-9_.-]', '_', brand_slug or '') or 'unknown'
            brand_folder = os.path.join(brand_pages_dir, safe_slug)
            os.makedirs(brand_folder, exist_ok=True)

            # Save the HTML file in the brand's folder with the slug in the filename
            html_filename = os.path.join(brand_folder, f"brand_page_{safe_slug}_{self.timestamp}.html")
            try:
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(f"✅ Saved brand page HTML to: {html_filename}")
            except Exception as e:
                self.logger.error(f"Failed to save brand page HTML: {e}")
        
        # Extract perfume URLs from this page
        page_perfume_urls = self._extract_perfume_urls(response)
        
        # Add to brand data (avoid duplicates using set)
        perfume_urls_set = brand_data['perfume_urls']
        new_urls = [url for url in page_perfume_urls if url not in perfume_urls_set]
        perfume_urls_set.update(new_urls)
        
        self.logger.info(f"Found {len(page_perfume_urls)} perfume links on page {current_page}")
        self.logger.info(f"Total unique perfume URLs so far: {len(brand_data['perfume_urls'])}")
        
        # Check for next page
        next_page_url = self._get_next_page_url(response)
        
        if next_page_url:
            self.logger.info(f"Found next page: {next_page_url}")

            # Follow next page using response.follow to preserve cookies/headers and handle relative URLs
            yield response.follow(
                next_page_url,
                callback=self.parse_brand_page,
                meta={
                    'brand_name': brand_name,
                    'brand_slug': brand_slug,
                    'country': country,  # Pass through metadata
                    'established': established,  # Pass through metadata
                    'description': description,  # Pass through metadata
                    'current_page': current_page + 1,
                    'dont_cache': False,
                },
                errback=self.handle_error,
            )
        else:
            # No more pages - yield BrandPageItem
            self.logger.info(f"✅ Finished scraping all pages for: {brand_name}")
            self.logger.info(f"   Pages scraped: {brand_data['pages_scraped']}")
            self.logger.info(f"   Perfume URLs collected: {len(brand_data['perfume_urls'])}")
            
            # Create and yield BrandPageItem
            yield self._create_brand_page_item(brand_data)
            
            # Perfume URLs collected - no longer following them in brand spider
            # Use parfumo_perfume_spider for detailed perfume scraping
            
            # Clean up brand data from memory
            del self.brand_page_data[brand_url_base]
        
        # Update stats
        self.crawler.stats.set_value('brand_pages_visited', self.brand_pages_visited)
    
    def handle_error(self, failure: Any) -> None:
        """Handle request failures with detailed logging."""
        # Standardize error logging format
        error_msg = f"REQUEST_FAILED | URL: {failure.request.url} | Type: {failure.type} | Value: {failure.value}"
        self.logger.error(error_msg)
        
        # Save error information
        error_filename = os.path.join(self.output_dir, f"brand_error_log_{self.timestamp}.txt")
        
        try:
            with open(error_filename, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().isoformat()}] {error_msg}\n")
                f.write("-" * 80 + "\n")
            
            self.logger.info(f"Error logged to: {error_filename}")
        except Exception as e:
            self.logger.error(f"Failed to save error log: {e}")
    
    def closed(self, reason: str) -> None:
        """
        Called when spider closes - log statistics.
        Feed Exports automatically handle JSON/CSV output.
        """
        self.logger.info(f"Brand spider closed: {reason}")
        self.logger.info(f"Total unique brands collected: {len(self.seen_brands)}")
        
        # Log statistics
        stats = self.crawler.stats.get_stats()
        self.logger.info("=" * 60)
        self.logger.info("BRAND SCRAPING STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Items scraped: {stats.get('item_scraped_count', 0)}")
        self.logger.info(f"Pages crawled: {stats.get('response_received_count', 0)}")
        self.logger.info(f"Unique brands: {len(self.seen_brands)}")
        self.logger.info(f"Brand pages visited: {self.brand_pages_visited}")
        self.logger.info(f"Duplicates found: {stats.get('item_scraped_count', 0) - len(self.seen_brands)}")
        self.logger.info("=" * 60)
        self.logger.info("✅ Output files created by Feed Exports:")
        self.logger.info("   - JSON: parfumo_dumps/brands_<timestamp>.json")
        self.logger.info("   - CSV:  parfumo_dumps/brands_<timestamp>.csv")
        self.logger.info("   - Brand pages: parfumo_dumps/brand_pages_<timestamp>.json")
        self.logger.info("=" * 60)
        self.logger.info("ℹ️  For perfume details, use: scrapy crawl parfumo_perfume_spider")
        self.logger.info("=" * 60)
    
    def _extract_perfume_urls(self, response: scrapy.http.Response) -> List[str]:
        """
        Extract perfume URLs from a brand page response.
        
        Args:
            response: Scrapy response object for a brand page
            
        Returns:
            List of perfume URLs found on the page
        """
        perfume_links = response.css('div.name > a[href*="/Perfumes/"]')
        page_perfume_urls = []
        
        for link in perfume_links:
            href = link.css('::attr(href)').get()
            if href and href.count('/') >= self.MIN_PERFUME_URL_DEPTH:  # Filter brand pages (only perfume detail pages)
                full_url = urljoin(response.url, href)
                page_perfume_urls.append(full_url)
        
        return page_perfume_urls
    
    def _get_next_page_url(self, response: scrapy.http.Response) -> Optional[str]:
        """
        Extract the next page URL from pagination links.
        
        Args:
            response: Scrapy response object for a brand page
            
        Returns:
            Next page URL if available, None otherwise
        """
        next_page_link = response.css('a[rel="next"].paging_links::attr(href)').get()
        if next_page_link:
            return urljoin(response.url, next_page_link)
        return None
    
    def _create_brand_page_item(self, brand_data: Dict[str, Any]) -> BrandPageItem:
        """
        Create a BrandPageItem from brand data.

        Args:
            brand_data: Dictionary containing brand page data

        Returns:
            BrandPageItem: Structured brand page data
        """
        loader = BrandPageItemLoader(item=BrandPageItem())
        loader.add_value('brand_name', brand_data['brand_name'])
        loader.add_value('brand_url', brand_data['brand_url'])
        loader.add_value('perfume_urls', list(brand_data['perfume_urls']))
        loader.add_value('pages_scraped', brand_data['pages_scraped'])
        loader.add_value('scraped_at', datetime.utcnow().isoformat())
        loader.add_value('scraped_by', self.name)

        # Add country of origin
        loader.add_value('country', brand_data.get('country', 'Unknown'))

        # Ensure established field is not None
        loader.add_value('established', brand_data.get('established') or 'Unknown')
        # Add brand description (may be 'Unknown' if not present)
        loader.add_value('description', brand_data.get('description') or 'Unknown')

        # Calculate total_perfumes within the loader (avoid unnecessary list cast)
        loader.add_value('total_perfumes', len(brand_data['perfume_urls']))

        return loader.load_item()