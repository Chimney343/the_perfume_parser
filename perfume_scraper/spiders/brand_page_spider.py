"""
Brand Page Spider for scraping a single brand's perfume listing page.
Similar to parfumo_spider's parse_brand_page method but as a standalone spider.
Handles pagination through all pages of a single brand.

Usage:
    poetry run scrapy crawl brand_page_spider -a url="https://www.parfumo.com/Perfumes/Dior"
"""

import scrapy
import os
import re
from datetime import datetime
from urllib.parse import urljoin
from typing import Dict, List, Set, Any, Optional, Generator

# Import Items and Loaders
from perfume_scraper.items import BrandPageItem
from perfume_scraper.loaders import BrandPageItemLoader


class BrandPageSpider(scrapy.Spider):
    name = 'brand_page_spider'
    allowed_domains = ['parfumo.com']
    
    # Constants for URL filtering
    MIN_PERFUME_URL_DEPTH = 4  # Minimum slashes to identify perfume detail pages
    
    def __init__(self, *args, **kwargs) -> None:
        super(BrandPageSpider, self).__init__(*args, **kwargs)
        self.timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir: str = "parfumo_dumps"
        
        # Dictionary to store brand page data during pagination
        # Key: brand_url, Value: dict with perfume_urls set and metadata
        self.brand_page_data: Dict[str, Dict[str, Any]] = {}
        
        # Get brand URL from parameter
        self.brand_url = kwargs.get('url')
        
        if not self.brand_url:
            raise ValueError("Missing required parameter: url (brand page URL)")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Brand URL: {self.brand_url}")
    
    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """Generate initial request for the brand page."""
        # Extract brand name from URL for logging
        # URL format: https://www.parfumo.com/Perfumes/BrandName
        brand_name = self.brand_url.split('/')[-1]
        
        yield scrapy.Request(
            url=self.brand_url,
            callback=self.parse_brand_page,
            meta={
                'brand_name': brand_name,
                'brand_slug': brand_name,
                'country': None,  # Will be extracted on first page
                'established': None,  # Will be extracted on first page
                'description': None,  # Will be extracted on first page
                'dont_cache': False,
            },
            errback=self.handle_error,
        )
    
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
            self.brand_page_data[brand_url_base] = {
                'brand_name': brand_name,
                'brand_url': brand_url_base,
                'perfume_urls': set(),  # Use set for O(1) lookups
                'pages_scraped': 0,
            }
            self.logger.info("=" * 80)
            self.logger.info(f"BRAND PAGE: {brand_name}")
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
        
        # Save the HTML for first page only (for debugging)
        if current_page == 1:
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
            
            # Clean up brand data from memory
            del self.brand_page_data[brand_url_base]
    
    def handle_error(self, failure: Any) -> None:
        """Handle request failures with detailed logging."""
        # Standardize error logging format
        error_msg = f"REQUEST_FAILED | URL: {failure.request.url} | Type: {failure.type} | Value: {failure.value}"
        self.logger.error(error_msg)
        
        # Save error information
        error_filename = os.path.join(self.output_dir, f"brand_page_error_log_{self.timestamp}.txt")
        
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
        self.logger.info(f"Brand page spider closed: {reason}")
        
        # Log statistics
        stats = self.crawler.stats.get_stats()
        self.logger.info("=" * 60)
        self.logger.info("BRAND PAGE SCRAPING STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Items scraped: {stats.get('item_scraped_count', 0)}")
        self.logger.info(f"Pages crawled: {stats.get('response_received_count', 0)}")
        self.logger.info("=" * 60)
        self.logger.info("✅ Output file created by Feed Exports:")
        self.logger.info("   - JSON: parfumo_dumps/brand_pages_<timestamp>.json")
        self.logger.info("   - CSV:  parfumo_dumps/brand_pages_<timestamp>.csv")
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

        # Add brand description
        loader.add_value('description', brand_data.get('description') or 'Unknown')

        # Calculate total_perfumes within the loader (avoid unnecessary list cast)
        loader.add_value('total_perfumes', len(brand_data['perfume_urls']))

        return loader.load_item()
