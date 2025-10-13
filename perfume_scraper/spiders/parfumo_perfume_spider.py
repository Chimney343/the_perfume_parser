"""
Parfumo Perfume Spider for scraping individual perfume data from parfumo.com.
This spider takes perfume URLs and extracts detailed perfume information including Charts data.
"""

import scrapy
import os
from datetime import datetime
from urllib.parse import urljoin

# Import Items
from perfume_scraper.items import PerfumeItem


class ParfumoPerfumeSpider(scrapy.Spider):
    name = 'parfumo_perfume_spider'
    allowed_domains = ['parfumo.com']
    
    # Custom settings for this spider - Enhanced anti-detection with Playwright
    custom_settings = {
        # Basic politeness settings
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 5,  # Moderate delay between requests
        'RANDOMIZE_DOWNLOAD_DELAY': True,  # Randomize delay (50-150% of DOWNLOAD_DELAY)
        
        # Concurrency settings - keep it conservative
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'CONCURRENT_REQUESTS_PER_IP': 1,
        
        # AutoThrottle for adaptive delays based on server response
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 3,
        'AUTOTHROTTLE_MAX_DELAY': 60,  # Max 60 seconds if server is slow
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.5,  # Very conservative
        'AUTOTHROTTLE_DEBUG': False,
        
        # Realistic browser user agent (Chrome on Windows)
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        
        # Cookie and session handling
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': False,
        
        # Retry settings
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 5,  # Retry up to 5 times
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403],  # Added 403 Forbidden
        'RETRY_PRIORITY_ADJUST': -1,
        
        # Download timeout
        'DOWNLOAD_TIMEOUT': 60,  # 60 seconds timeout
        
        # HTTP cache to avoid re-downloading
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 86400,  # Cache for 24 hours
        'HTTPCACHE_DIR': 'httpcache',
        'HTTPCACHE_IGNORE_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403],
        
        # Redirect settings
        'REDIRECT_ENABLED': True,
        'REDIRECT_MAX_TIMES': 3,
        
        # HTTP compression
        'COMPRESSION_ENABLED': True,
        
        # Telnet console disabled for production
        'TELNETCONSOLE_ENABLED': False,
        
        # Logging
        'LOG_LEVEL': 'INFO',
        'LOG_ENABLED': True,
        
        # Default request headers (will be merged with custom headers)
        'DEFAULT_REQUEST_HEADERS': {
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
        },
        
        # Item Pipelines - Process items through validation, cleaning, and export
        'ITEM_PIPELINES': {
            'perfume_scraper.pipelines.ValidationPipeline': 300,
            'perfume_scraper.pipelines.DataCleaningPipeline': 400,
            'perfume_scraper.pipelines.DuplicatesPipeline': 500,
            'perfume_scraper.pipelines.PerfumeJsonExportPipeline': 600,  # Individual perfume files
            'perfume_scraper.pipelines.StatisticsPipeline': 800,
        },
        
        # Playwright settings for JavaScript rendering (Charts data)
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'args': ['--no-sandbox', '--disable-dev-shm-usage']
        },
    }
    
    def __init__(self, *args, **kwargs):
        super(ParfumoPerfumeSpider, self).__init__(*args, **kwargs)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = "parfumo_dumps"
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"Output directory: {self.output_dir}")
    
    def start_requests(self):
        """
        Generate requests from perfume URLs.
        Can be provided via command line argument or input file.
        
        Usage examples:
        scrapy crawl parfumo_perfume_spider -a url="https://www.parfumo.com/Perfumes/Baldi/Lapislazzuli"
        scrapy crawl parfumo_perfume_spider -a urls_file="perfume_urls.txt"
        """
        # Get URLs from command line argument
        url = getattr(self, 'url', None)
        urls_file = getattr(self, 'urls_file', None)
        
        urls_to_scrape = []
        
        if url:
            # Single URL from command line
            urls_to_scrape.append(url)
        elif urls_file:
            # Multiple URLs from file
            try:
                with open(urls_file, 'r', encoding='utf-8') as f:
                    urls_to_scrape = [line.strip() for line in f if line.strip()]
                self.logger.info(f"Loaded {len(urls_to_scrape)} URLs from {urls_file}")
            except FileNotFoundError:
                self.logger.error(f"URLs file not found: {urls_file}")
                return
        else:
            # Default test URL if nothing specified
            urls_to_scrape = ["https://www.parfumo.com/Perfumes/Baldi/Lapislazzuli"]
            self.logger.info("No URLs specified, using default test URL")
        
        for url in urls_to_scrape:
            # Extract brand and perfume info from URL
            url_parts = url.split('/')
            brand_name = url_parts[-2] if len(url_parts) >= 2 else 'Unknown'
            perfume_slug = url_parts[-1] if len(url_parts) >= 1 else 'unknown'
            
            yield scrapy.Request(
                url=url,
                callback=self.parse_perfume,
                meta={
                    'brand_name': brand_name.replace('_', ' ').replace('-', ' '),
                    'brand_slug': brand_name,
                    'perfume_slug': perfume_slug,
                    'dont_cache': False,
                    # Add Playwright for Charts data extraction
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                        "timeout": 30000,
                    },
                },
                errback=self.handle_error,
            )
    
    async def parse_perfume(self, response):
        """
        Parse individual perfume page to extract detailed information.
        
        Extracts:
        - Perfume name and brand
        - Main accords
        - Fragrance pyramid (top/heart/base notes)
        - Perfumer
        - Ratings (scent, longevity, sillage, bottle, overall)
        - Charts/Classification data (via Playwright)
        
        Args:
            response: Scrapy response object for a perfume page
            
        Yields:
            PerfumeItem: Structured perfume data
        """
        brand_name = response.meta.get('brand_name', 'Unknown')
        brand_slug = response.meta.get('brand_slug', 'unknown')
        perfume_slug = response.meta.get('perfume_slug', 'unknown')
        
        self.logger.info("=" * 80)
        self.logger.info(f"PERFUME: {perfume_slug} (Brand: {brand_name})")
        self.logger.info(f"URL: {response.url}")
        self.logger.info("=" * 80)
        
        # Save HTML for debugging (optional - comment out in production)
        if False:  # Set to True to save HTML files
            html_filename = f"{self.output_dir}/perfume_{brand_slug}_{perfume_slug}_{self.timestamp}.html"
            try:
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                self.logger.info(f"✅ Saved perfume HTML to: {html_filename}")
            except Exception as e:
                self.logger.error(f"Failed to save perfume HTML: {e}")
        
        # Create PerfumeItem
        item = PerfumeItem()
        
        # Extract perfume name from h1
        perfume_name = response.css('h1.p_name_h1[itemprop="name"]::text').get()
        if perfume_name:
            perfume_name = perfume_name.strip()
        
        item['name'] = perfume_name
        item['brand'] = brand_name
        item['url'] = response.url
        
        # Extract description (handle nested links and elements)
        description_element = response.css('span[itemprop="description"]')
        if description_element:
            # Get all text content, including from nested elements
            description_texts = description_element.css('::text').getall()
            # Filter out empty strings and join
            description_parts = [t.strip() for t in description_texts if t.strip()]
            description = ' '.join(description_parts)
            
            # Clean up common UI elements that get included
            # Stop at common endings or remove UI elements
            ui_elements = ['Pronunciation', 'Compare', 'Add to', 'Wishlist']
            for ui_elem in ui_elements:
                if ui_elem in description:
                    description = description.split(ui_elem)[0]
            
            # Remove extra whitespace and clean up
            description = ' '.join(description.split()).strip()
            if description:
                item['description'] = description
        
        # Extract gender from description or icon
        # Pattern: "for women and men", "for men", "for women"
        if description and 'for' in description:
            gender_part = description.split('for')[1].split('.')[0].strip()
            item['gender'] = gender_part
        
        # Extract perfumer
        perfumer_link = response.css('div.w-100.mt-0-5.mb-3 a')
        if perfumer_link:
            perfumer_name = perfumer_link.css('::text').get()
            perfumer_url = perfumer_link.css('::attr(href)').get()
            if perfumer_name:
                item['perfumer'] = perfumer_name.strip()
            if perfumer_url:
                item['perfumer_url'] = urljoin(response.url, perfumer_url)
        
        # Extract main accords
        # Structure: <div class="s-circle-container"><div class="s-circle" style="background: #color"></div><div class="text-xs grey">Accord Name</div></div>
        main_accords = []
        accord_containers = response.css('div.s-circle-container')
        for container in accord_containers:
            accord_name = container.css('div.text-xs.grey::text').get()
            circle_style = container.css('div.s-circle::attr(style)').get()
            
            # Determine intensity from circle size class
            circle_classes = container.css('div.s-circle::attr(class)').get()
            intensity = 'medium'
            if 's-circle_l' in circle_classes:
                intensity = 'large'
            elif 's-circle_m' in circle_classes:
                intensity = 'medium'
            elif 's-circle_s' in circle_classes:
                intensity = 'small'
            
            if accord_name:
                main_accords.append({
                    'name': accord_name.strip(),
                    'intensity': intensity
                })
        
        item['main_accords'] = main_accords
        
        # Extract fragrance notes
        # Initialize variables to avoid UnboundLocalError
        top_notes = []
        heart_notes = []
        base_notes = []
        
        # Check if there's a pyramid structure or a simple notes list
        has_pyramid = bool(response.css('div.pyramid_block').get())
        
        if has_pyramid:
            # Extract from pyramid structure (top/heart/base)
            # Top notes
            top_notes = []
            top_section = response.css('div.pyramid_block.nb_t div.right span.clickable_note_img')
            for note in top_section:
                note_name = note.css('span.nowrap span::text').get()
                if not note_name:  # Try alternative structure
                    note_name = note.css('::text').getall()
                    note_name = ''.join([t.strip() for t in note_name if t.strip()])
                if note_name:
                    top_notes.append(note_name.strip())
            
            # Heart notes
            heart_notes = []
            heart_section = response.css('div.pyramid_block.nb_m div.right span.clickable_note_img')
            for note in heart_section:
                note_name = note.css('span.nowrap span::text').get()
                if not note_name:
                    note_name = note.css('::text').getall()
                    note_name = ''.join([t.strip() for t in note_name if t.strip()])
                if note_name:
                    heart_notes.append(note_name.strip())
            
            # Base notes
            base_notes = []
            base_section = response.css('div.pyramid_block.nb_b div.right span.clickable_note_img')
            for note in base_section:
                note_name = note.css('span.nowrap span::text').get()
                if not note_name:
                    note_name = note.css('::text').getall()
                    note_name = ''.join([t.strip() for t in note_name if t.strip()])
                if note_name:
                    base_notes.append(note_name.strip())
            
            item['top_notes'] = top_notes
            item['heart_notes'] = heart_notes
            item['base_notes'] = base_notes
        else:
            # Extract from simple notes list (no pyramid)
            # Structure: <div class="notes_list"><div class="nb_n"><span class="clickable_note_img"><span class="nowrap">Note Name</span></span> ...</div></div>
            all_notes = []
            notes_section = response.css('div.notes_list div.nb_n span.clickable_note_img span.nowrap')
            for note in notes_section:
                # Get text after the image
                note_text_parts = note.css('::text').getall()
                note_name = ''.join([t.strip() for t in note_text_parts if t.strip()])
                if note_name:
                    all_notes.append(note_name.strip())
            
            # When there's no pyramid, put all notes in top_notes
            item['top_notes'] = all_notes
            item['heart_notes'] = []
            item['base_notes'] = []
        
        # Extract ratings
        # Scent rating
        scent_elem = response.css('div.barfiller_element[data-type="scent"]')
        if scent_elem:
            score = scent_elem.css('span.bold.blue::text').get()
            votes_text = scent_elem.css('span.lightgrey.text-2xs::text').get()
            if score and votes_text:
                votes = votes_text.split()[0]  # Extract number before "Ratings"
                item['rating_scent'] = {'score': score.strip(), 'votes': votes.strip()}
        
        # Longevity rating
        longevity_elem = response.css('div.barfiller_element[data-type="durability"]')
        if longevity_elem:
            score = longevity_elem.css('span.bold.pink::text').get()
            votes_text = longevity_elem.css('span.lightgrey.text-2xs::text').get()
            if score and votes_text:
                votes = votes_text.split()[0]
                item['rating_longevity'] = {'score': score.strip(), 'votes': votes.strip()}
        
        # Sillage rating
        sillage_elem = response.css('div.barfiller_element[data-type="sillage"]')
        if sillage_elem:
            score = sillage_elem.css('span.bold.purple::text').get()
            votes_text = sillage_elem.css('span.lightgrey.text-2xs::text').get()
            if score and votes_text:
                votes = votes_text.split()[0]
                item['rating_sillage'] = {'score': score.strip(), 'votes': votes.strip()}
        
        # Bottle rating
        bottle_elem = response.css('div.barfiller_element[data-type="bottle"]')
        if bottle_elem:
            score = bottle_elem.css('span.bold.green::text').get()
            votes_text = bottle_elem.css('span.lightgrey.text-2xs::text').get()
            if score and votes_text:
                votes = votes_text.split()[0]
                item['rating_bottle'] = {'score': score.strip(), 'votes': votes.strip()}
        
        # Overall/General rating (aggregate rating)
        overall_rating_elem = response.css('div[itemprop="aggregateRating"]')
        if overall_rating_elem:
            # Overall rating score (e.g., "8.4")
            overall_score = overall_rating_elem.css('span[itemprop="ratingValue"]::text').get()
            if overall_score:
                item['rating_overall'] = overall_score.strip()
            
            # Total rating count (e.g., "12 Ratings")
            rating_count_text = overall_rating_elem.css('span[itemprop="ratingCount"]::text').get()
            if rating_count_text:
                # Extract just the number from "12 Ratings"
                rating_count = rating_count_text.split()[0]
                item['rating_count'] = rating_count.strip()
        
        # Extract Charts/Classification data if available
        try:
            charts_data = await self.extract_charts_data(response)
            if charts_data:
                item.update(charts_data)
                self.logger.info(f"📊 Charts data extracted for: {perfume_name}")
            else:
                self.logger.info(f"📊 No Charts data available for: {perfume_name}")
        except Exception as e:
            self.logger.warning(f"📊 Charts extraction failed for {perfume_name}: {e}")
            # Set chart fields to None if extraction fails
            item['chart_type'] = None
            item['chart_style'] = None 
            item['chart_season'] = None
            item['chart_occasion'] = None
        
        # Add metadata
        item['scraped_at'] = datetime.utcnow().isoformat()
        item['scraped_by'] = self.name
        
        # Log extracted data summary
        self.logger.info(f"✅ Extracted: {perfume_name}")
        self.logger.info(f"   Accords: {len(main_accords)}")
        self.logger.info(f"   Notes: Top={len(top_notes)}, Heart={len(heart_notes)}, Base={len(base_notes)}")
        self.logger.info(f"   Perfumer: {item.get('perfumer', 'N/A')}")
        self.logger.info("=" * 80)
        
        yield item
    
    async def extract_charts_data(self, response):
        """
        Extract Charts/Classification data using Playwright.
        Returns dict with chart_type, chart_style, chart_season, chart_occasion fields.
        """
        charts_data = {
            'chart_type': None,
            'chart_style': None, 
            'chart_season': None,
            'chart_occasion': None
        }
        
        try:
            # Get Playwright page from response meta
            page = response.meta.get("playwright_page")
            if not page:
                self.logger.warning("No Playwright page available for Charts extraction")
                return charts_data
            
            self.logger.info("🔍 Extracting Charts data with Playwright...")
            
            # Look for Charts section using text content (more reliable than ID)
            try:
                charts_heading = page.locator('h2:has-text("Charts")')
                charts_count = await charts_heading.count()
                
                if charts_count == 0:
                    self.logger.debug("No Charts heading found - perfume has no charts data")
                    return charts_data
                    
                self.logger.debug(f"Found {charts_count} Charts heading(s)")
                
                # Scroll to Charts section to ensure it's in viewport
                await charts_heading.first.scroll_into_view_if_needed()
                
                # Wait for any initial content to load
                await page.wait_for_timeout(2000)
                
                # Look for toggle buttons (indicates charts are available)
                pie_button = page.locator('.toggle_chart[data-type="pie"]')
                radar_button = page.locator('.toggle_chart[data-type="radar"]')
                
                pie_count = await pie_button.count()
                radar_count = await radar_button.count()
                
                if pie_count == 0 and radar_count == 0:
                    self.logger.debug("No chart toggle buttons found - no interactive charts available")
                    return charts_data
                
                self.logger.debug(f"Found chart buttons: pie={pie_count}, radar={radar_count}")
                
                # Get classification holder element
                classification_holder = page.locator('#classification_holder_am')
                holder_count = await classification_holder.count()
                
                if holder_count == 0:
                    self.logger.debug("No classification holder found")
                    return charts_data
                
                # Ensure pie chart is selected (usually default)
                if pie_count > 0:
                    pie_classes = await pie_button.first.get_attribute("class") or ""
                    if "active" not in pie_classes:
                        self.logger.debug("Activating pie chart...")
                        await pie_button.first.click()
                        await page.wait_for_timeout(2000)
                
                # Wait for AJAX content to load
                max_wait_attempts = 10
                for attempt in range(max_wait_attempts):
                    chart_html = await classification_holder.first.inner_html()
                    
                    # Check if content is loaded (not just ajax loader)
                    if ("ajax_loader" not in chart_html and 
                        len(chart_html.strip()) > 100 and
                        "white-box-padding" not in chart_html):
                        
                        self.logger.info(f"📊 Charts content loaded ({len(chart_html)} chars)")
                        
                        # Save chart HTML for debugging/analysis
                        perfume_slug = response.meta.get('perfume_slug', 'unknown')
                        debug_file = f"chart_debug_{perfume_slug}_{self.timestamp}.html"
                        
                        try:
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(chart_html)
                            self.logger.info(f"💾 Saved chart HTML to: {debug_file}")
                        except Exception as e:
                            self.logger.warning(f"Failed to save chart debug file: {e}")
                        
                        # Parse the chart data
                        charts_data = self._parse_chart_html(chart_html)
                        if any(charts_data.values()):
                            self.logger.info("📊 Successfully extracted Charts data!")
                        else:
                            self.logger.info("📊 Charts content found but no parseable data")
                        
                        return charts_data
                    
                    elif attempt < max_wait_attempts - 1:
                        self.logger.debug(f"Charts still loading... attempt {attempt + 1}/{max_wait_attempts}")
                        await page.wait_for_timeout(1000)
                
                self.logger.debug("Charts content did not fully load within timeout")
                
            except Exception as e:
                self.logger.debug(f"Error during Charts extraction: {e}")
            
        except Exception as e:
            self.logger.warning(f"Charts extraction failed: {e}")
            
        return charts_data
    
    def _parse_chart_html(self, chart_html):
        """Parse the Charts HTML content to extract classification percentages."""
        charts_data = {
            'chart_type': None,
            'chart_style': None,
            'chart_season': None, 
            'chart_occasion': None
        }
        
        try:
            from scrapy import Selector
            
            # Create Selector from the chart HTML
            selector = Selector(text=chart_html)
            
            # Look for different chart data structures
            # This is a starting implementation - will need refinement based on actual HTML
            
            # Try to find chart sections or data tables
            chart_sections = selector.css('.chart-section, .classification-section, .chart-data')
            
            if chart_sections:
                self.logger.debug(f"Found {len(chart_sections)} chart sections")
                
                # Try to extract key-value pairs for different categories
                for section in chart_sections:
                    section_text = section.get()
                    
                    # Look for type indicators (EDT, EDP, etc.)
                    if any(term in section_text.upper() for term in ['EDT', 'EDP', 'PARFUM', 'COLOGNE']):
                        charts_data['chart_type'] = self._extract_classification_data(section, 'type')
                    
                    # Look for style indicators
                    elif any(term in section_text.upper() for term in ['FRESH', 'ORIENTAL', 'WOODY', 'FLORAL']):
                        charts_data['chart_style'] = self._extract_classification_data(section, 'style')
                    
                    # Look for season indicators
                    elif any(term in section_text.upper() for term in ['SPRING', 'SUMMER', 'AUTUMN', 'WINTER']):
                        charts_data['chart_season'] = self._extract_classification_data(section, 'season')
                    
                    # Look for occasion indicators
                    elif any(term in section_text.upper() for term in ['DAILY', 'EVENING', 'OFFICE', 'PARTY']):
                        charts_data['chart_occasion'] = self._extract_classification_data(section, 'occasion')
            
            # Alternative: look for structured data or JSON
            json_data = selector.re(r'data-chart="([^"]*)"')
            if json_data:
                import json
                try:
                    parsed_data = json.loads(json_data[0])
                    self.logger.debug("Found JSON chart data")
                    # Process JSON data structure
                    charts_data.update(self._process_json_chart_data(parsed_data))
                except:
                    pass
            
            # Log what we found
            found_data = {k: v for k, v in charts_data.items() if v is not None}
            if found_data:
                self.logger.info(f"Parsed chart data: {found_data}")
            else:
                self.logger.debug("No parseable chart data found in HTML")
            
        except Exception as e:
            self.logger.warning(f"Error parsing chart HTML: {e}")
        
        return charts_data
    
    def _extract_classification_data(self, section, category):
        """Extract classification percentages from a chart section."""
        try:
            # This is a placeholder implementation
            # Will need to be refined based on actual HTML structure
            
            # Look for percentage data
            percentages = section.re(r'(\d+(?:\.\d+)?)%')
            labels = section.css('::text').getall()
            
            if percentages and labels:
                # Create a simple classification dict
                classification = {}
                for i, pct in enumerate(percentages[:5]):  # Limit to top 5
                    if i < len(labels):
                        label = labels[i].strip()
                        if label and len(label) > 1:
                            classification[label] = f"{pct}%"
                
                return classification if classification else None
                
        except Exception as e:
            self.logger.debug(f"Error extracting {category} classification: {e}")
        
        return None
    
    def _process_json_chart_data(self, json_data):
        """Process JSON chart data if available."""
        processed = {}
        
        try:
            # This will depend on the actual JSON structure
            if isinstance(json_data, dict):
                for key, value in json_data.items():
                    if 'type' in key.lower():
                        processed['chart_type'] = value
                    elif 'style' in key.lower():
                        processed['chart_style'] = value
                    elif 'season' in key.lower():
                        processed['chart_season'] = value
                    elif 'occasion' in key.lower():
                        processed['chart_occasion'] = value
        except Exception as e:
            self.logger.debug(f"Error processing JSON chart data: {e}")
        
        return processed
    
    def handle_error(self, failure):
        """Handle request failures with detailed logging."""
        self.logger.error(f"Request failed: {failure.request.url}")
        self.logger.error(f"Failure type: {failure.type}")
        self.logger.error(f"Failure value: {failure.value}")
        
        # Save error information
        error_filename = f"{self.output_dir}/perfume_error_log_{self.timestamp}.txt"
        
        try:
            with open(error_filename, 'a', encoding='utf-8') as f:
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"URL: {failure.request.url}\n")
                f.write(f"Error: {failure.type} - {failure.value}\n")
                f.write("-" * 50 + "\n")
            
            self.logger.info(f"Error logged to: {error_filename}")
        except Exception as e:
            self.logger.error(f"Failed to save error log: {e}")
    
    def closed(self, reason):
        """Called when spider closes - log statistics."""
        self.logger.info(f"Perfume spider closed: {reason}")
        
        # Log statistics
        stats = self.crawler.stats.get_stats()
        self.logger.info("=" * 60)
        self.logger.info("PERFUME SCRAPING STATISTICS")
        self.logger.info("=" * 60)
        self.logger.info(f"Perfumes scraped: {stats.get('item_scraped_count', 0)}")
        self.logger.info(f"Pages crawled: {stats.get('response_received_count', 0)}")
        self.logger.info("=" * 60)