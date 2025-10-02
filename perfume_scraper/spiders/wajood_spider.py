import scrapy
import re
import urllib.parse
from scrapy import Request
from perfume_scraper.items import PerfumeItem
from datetime import datetime

class PerfumeSpider(scrapy.Spider):
    name = 'perfume_data'
    allowed_domains = ['fragrantica.com']

    def start_requests(self):
        urls = [
            'https://www.fragrantica.com/perfume/Lattafa-Perfumes/Wajood-80467.html'
        ]
        for url in urls:
            yield Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        # 1. Wait for the “Show Diagram” switch and click it
                        ("wait_for_selector", "#showDiagram"),
                        ("eval_on_selector", "#showDiagram", "el => el.click()"),
                        # 2. Wait for pyramid levels
                        ("wait_for_selector", "pyramid-level[notes]"),
                        # 3. Wait for the description container
                        ("wait_for_selector", "[itemprop='description']"),
                        # 4. Click “Show more” if present
                        ("eval_on_selector", ".show-more-button", 
                            "el => el.click()", {"timeout": 10000}),
                        # 5. Wait a moment for expanded text
                        ("wait_for_timeout", 500),
                    ],
                },
                callback=self.parse,
                errback=self.errback,
            )

    async def parse(self, response):
        page = response.meta.get("playwright_page")
        if page:
            # Dump the full rendered HTML
            html = await page.content()
            file_name = "rendered_wajood.html"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(html)
            self.logger.info(f"Saved rendered HTML to {file_name}")
            # Then close the page
            await page.close()
        
        self.logger.info(f"Response status: {response.status}")
        
        item = PerfumeItem()

        # Basic perfume information
        item['name'] = self.extract_text(response, 'h1[itemprop="name"] ::text')
        item['brand'] = self.extract_text(response, '[itemprop="brand"] [itemprop="name"] ::text')
        item['launch_year'] = self.extract_launch_year(response)
        item['perfumer'] = self.extract_text(response, '.perfumer ::text')
        item['gender'] = self.extract_gender(response)
        item['fragrance_family'] = self.extract_fragrance_family(response)
        item['url'] = response.url
        item['fragrance_id'] = self.extract_fragrance_id(response.url)

        # Description
        item['description'] = self.extract_description(response)

        # Notes
        item['notes_pyramid'] = self.extract_notes_pyramid(response)

        # Main accords
        item['main_accords'] = self.extract_main_accords(response)

        # Ratings
        item['ratings'] = {
            'overall_rating': self.extract_float(response, '[itemprop="ratingValue"] ::text'),
            'best_rating': self.extract_float(response, '[itemprop="bestRating"] ::text'),
            'rating_count': self.extract_int(response, '[itemprop="ratingCount"] ::attr(content)'),
            'review_count': self.extract_int(response, '[itemprop="reviewCount"] ::attr(content)'),
            'longevity': self.extract_longevity_votes(response),
            'sillage': self.extract_sillage_votes(response),
            'gender': self.extract_gender_votes(response),
            'price': self.extract_price_votes(response),
        }


        # Images
        item['images'] = {
            'main_image': self.extract_text(response, '[itemprop="image"] ::attr(src)'),
            'bottle_images': self.extract_all_text(response, 'picture img ::attr(src)'),
            'social_card': self.extract_text(response, 'meta[property="og:image"] ::attr(content)'),
        }

        # Reviews
        item['reviews'] = {
            'total_reviews': len(response.css('.fragrance-review-box')),
            'recent_reviews': self.extract_recent_reviews(response, limit=5)
        }

        # Recommendations
        item['recommendations'] = {
            'similar_fragrances': self.extract_similar_fragrances(response),
            'designer_fragrances': self.extract_designer_fragrances(response),
            'people_also_like': self.extract_people_also_like(response)
        }

        # Brand info
        item['brand_info'] = {
            'brand_name': item['brand'],
            'brand_logo': self.extract_text(response, '.brand-logo ::attr(src)'),
            'brand_url': self.extract_text(response, '[itemprop="brand"] [itemprop="url"] ::attr(href)'),
        }

        # Collections
        item['collections'] = self.extract_collections(response)

        # Availability
        item['availability'] = {
            'buy_links': self.extract_buy_links(response),
            'price_comparison': self.extract_price_info(response)
        }

        # Metadata
        item['metadata'] = {
            'canonical_url': self.extract_text(response, 'link[rel="canonical"] ::attr(href)'),
            'alternate_languages': self.extract_language_versions(response),
            'schema_type': 'Product',
            'extraction_date': self.get_current_date()
        }

        self.logger.info(f"Successfully scraped: {item.get('name')}")
        yield item

    async def errback(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure.value}")

    # Helper extraction methods
    def extract_text(self, response, selector):
        result = response.css(selector).get()
        return result.strip() if result else None

    def extract_description(self, response):
        """
        Extracts the meta description content from the page head.
        """
        desc = response.xpath("//meta[@name='description']/@content").get()
        return desc.strip() if desc else None


    def extract_all_text(self, response, selector):
        results = response.css(selector).getall()
        return [text.strip() for text in results if text.strip()]

    def extract_float(self, response, selector):
        text = self.extract_text(response, selector)
        if text:
            try:
                return float(text)
            except ValueError:
                return None
        return None

    def extract_int(self, response, selector):
        text = self.extract_text(response, selector)
        if text:
            try:
                return int(text)
            except ValueError:
                return None
        return None

    def extract_launch_year(self, response):
        description = self.extract_text(response, '[itemprop="description"] ::text')
        if description:
            year_match = re.search(r'launched in (\d{4})', description)
            if year_match:
                return int(year_match.group(1))
        return None

    def extract_fragrance_id(self, url):
        match = re.search(r'-(\d+)\.html', url)
        return int(match.group(1)) if match else None

    def extract_gender(self, response):
        title = self.extract_text(response, 'title ::text') or ""
        if 'for women and men' in title.lower():
            return 'unisex'
        elif 'for women' in title.lower():
            return 'women'
        elif 'for men' in title.lower():
            return 'men'
        return None

    def extract_fragrance_family(self, response):
        description = self.extract_text(response, '[itemprop="description"] ::text')
        if description:
            family_match = re.search(r'is a ([^.]+) fragrance', description)
            if family_match:
                return family_match.group(1).strip()
        return None



    def extract_notes_pyramid(self, response):
        """
        Returns {'top': [...], 'middle': [...], 'base': [...]},
        where each value is a list of human-readable note names.
        """
        levels = {
            'top':    'Top Notes',
            'middle': 'Middle Notes',
            'base':   'Base Notes',
        }
        pyramid = {}
        # Precompile regex to extract slug from URL
        pattern = re.compile(r'/notes/([A-Za-z0-9-]+)-\d+\.html')
        for key, label in levels.items():
            xpath = (
                f"//h4[b/text() = '{label}']"
                f"/following-sibling::div[1]"
                f"//a[contains(@href, '/notes/')]/@href"
            )
            hrefs = response.xpath(xpath).getall()
            seen, names = set(), []
            for href in hrefs:
                match = pattern.search(href)
                if not match:
                    continue
                slug = match.group(1)           # e.g. "Sea-Water"
                name = slug.replace('-', ' ')   # -> "Sea Water"
                if name not in seen:
                    seen.add(name)
                    names.append(name)
            pyramid[key] = names
        return pyramid

    def extract_main_accords(self, response):
        accords = []
        accord_bars = response.css('.accord-bar')
        for bar in accord_bars:
            name = bar.css('::text').get()
            if not name:
                name = bar.css('::attr(class)').re_first(r'accord-bar\s+([\w\s-]+)')
            style = bar.css('::attr(style)').get() or ""
            width_match = re.search(r'width:\s*([\d.]+)', style)
            if name and width_match:
                accords.append({'name': name.strip(), 'intensity': float(width_match.group(1))})
        return accords

    def extract_longevity_votes(self, response):
        """
        Returns a dict mapping vote label → count for the Longevity section.
        Example:
        {
            "very weak": 5,
            "weak": 4,
            "moderate": 60,
            "long lasting": 221,
            "eternal": 87
        }
        """
        votes = {}
        # 1) Find the container that has the "LONGEVITY" label
        container_xpath = (
            "//span[normalize-space(text())='LONGEVITY']"
            "/ancestor::div[2]"  # up to the wrapper div
            "//div[contains(@class, 'grid-x grid-margin-x')]"  # each vote row
        )
        rows = response.xpath(container_xpath)
        for row in rows:
            # label text
            label = row.xpath(".//span[@class='vote-button-name']/text()").get()
            # count text
            count = row.xpath(".//span[@class='vote-button-legend']/text()").get()
            try:
                votes[label.strip()] = int(count)
            except (TypeError, ValueError):
                continue
        return votes

    def extract_sillage_votes(self, response):
        """
        Returns a dict mapping vote label → count for the Sillage section.
        Example:
        {
            "intimate": 10,
            "moderate": 105,
            "strong": 214,
            "enormous": 43
        }
        """
        votes = {}
        # 1) Find the container that has the "SILLAGE" label
        container_xpath = (
            "//span[normalize-space(text())='SILLAGE']"
            "/ancestor::div[2]"  # up to wrapper div
            "//div[contains(@class, 'grid-x grid-margin-x')]"  # vote rows
        )
        rows = response.xpath(container_xpath)
        for row in rows:
            label = row.xpath(".//span[@class='vote-button-name']/text()").get()
            count = row.xpath(".//span[@class='vote-button-legend']/text()").get()
            try:
                votes[label.strip()] = int(count)
            except (TypeError, ValueError):
                continue
        return votes

    def extract_gender_votes(self, response):
        """
        Returns a dict mapping gender vote label → count for the GENDER section.
        Example:
        {
            "female": 10,
            "more female": 1,
            "unisex": 26,
            "more male": 100,
            "male": 261
        }
        """
        votes = {}
        container_xpath = (
            "//span[normalize-space(text())='GENDER']"
            "/ancestor::div[2]"
            "//div[contains(@class, 'grid-x grid-margin-x')]"
        )
        rows = response.xpath(container_xpath)
        for row in rows:
            label = row.xpath(".//span[@class='vote-button-name']/text()").get()
            count = row.xpath(".//span[@class='vote-button-legend']/text()").get()
            try:
                votes[label.strip()] = int(count)
            except (TypeError, ValueError):
                continue
        return votes

    def extract_price_votes(self, response):
        """
        Returns a dict mapping price vote label → count for the PRICE VALUE section.
        Example:
        {
            "way overpriced": 12,
            "overpriced": 7,
            "ok": 39,
            "good value": 141,
            "great value": 172
        }
        """
        votes = {}
        container_xpath = (
            "//span[normalize-space(text())='PRICE VALUE']"
            "/ancestor::div[2]"
            "//div[contains(@class, 'grid-x grid-margin-x')]"
        )
        rows = response.xpath(container_xpath)
        for row in rows:
            label = row.xpath(".//span[@class='vote-button-name']/text()").get()
            count = row.xpath(".//span[@class='vote-button-legend']/text()").get()
            try:
                votes[label.strip()] = int(count)
            except (TypeError, ValueError):
                continue
        return votes


    def extract_recent_reviews(self, response, limit=5):
        reviews = []
        review_boxes = response.css('.fragrance-review-box')[:limit]
        for box in review_boxes:
            review = {
                'author': box.css('[itemprop="name"] ::attr(content)').get(),
                'date': box.css('[itemprop="datePublished"] ::attr(content)').get(),
                'rating': self.extract_review_rating(box),
                'text': self.clean_review_text(box.css('[itemprop="reviewBody"] ::text').getall()),
                'votes': self.extract_review_votes(box)
            }
            reviews.append(review)
        return reviews

    def extract_review_rating(self, review_element):
        rating = review_element.css('[itemprop="ratingValue"] ::attr(content)').get()
        if rating:
            try:
                return int(rating)
            except ValueError:
                return None
        return None

    def clean_review_text(self, text_list):
        if text_list:
            combined_text = ' '.join([t.strip() for t in text_list if t.strip()])
            cleaned = re.sub(r'\s+', ' ', combined_text).strip()
            return cleaned[:500] + '...' if len(cleaned) > 500 else cleaned
        return None

    def extract_review_votes(self, review_element):
        return {'helpful': None, 'unhelpful': None}

    def extract_similar_fragrances(self, response):
        similar = []
        carousel_items = response.css('#similar-perfumes .carousel-cell, [class*="similar"] .carousel-cell')
        for item in carousel_items:
            fragrance = {
                'name': item.css('img ::attr(alt)').get(),
                'brand': item.css('.brand ::text').get(),
                'url': item.css('a ::attr(href)').get(),
                'image': item.css('img ::attr(src)').get()
            }
            if fragrance['name']:
                similar.append(fragrance)
        return similar

    def extract_designer_fragrances(self, response):
        designer_fragrances = []
        designer_carousel = response.css('.carousel .carousel-cell')
        for item in designer_carousel:
            fragrance = {
                'name': item.css('img ::attr(alt)').get(),
                'url': item.css('a ::attr(href)').get(),
                'image': item.css('img ::attr(src)').get()
            }
            if fragrance['name'] and fragrance['url']:
                designer_fragrances.append(fragrance)
        return designer_fragrances

    def extract_people_also_like(self, response):
        also_like = []
        also_like_section = response.css('[class*="also-like"] .carousel-cell, [class*="people"] .carousel-cell')
        for item in also_like_section:
            fragrance = {
                'name': item.css('img ::attr(alt)').get(),
                'brand': item.css('.brand ::text').get(),
                'url': item.css('a ::attr(href)').get()
            }
            if fragrance['name']:
                also_like.append(fragrance)
        return also_like

    def extract_collections(self, response):
        collections = []
        collection_elements = response.css('[class*="collection"] a')
        for element in collection_elements:
            collection = {
                'name': element.css('::text').get(),
                'url': element.css('::attr(href)').get()
            }
            if collection['name']:
                collections.append(collection)
        return collections

    def extract_buy_links(self, response):
        buy_links = []
        link_elements = response.css('a[href*="buy"], a[href*="purchase"], a[href*="shop"]')
        for link in link_elements:
            buy_links.append({
                'text': link.css('::text').get(),
                'url': link.css('::attr(href)').get()
            })
        return buy_links

    def extract_price_info(self, response):
        prices = []
        price_elements = response.css('[class*="price"], [data-price]')
        for element in price_elements:
            price_text = element.css('::text').get()
            if price_text and ('$' in price_text or '€' in price_text or '£' in price_text):
                prices.append(price_text.strip())
        return prices

    def extract_language_versions(self, response):
        languages = {}
        alt_links = response.css('link[rel="alternate"]')
        for link in alt_links:
            hreflang = link.css('::attr(hreflang)').get()
            href = link.css('::attr(href)').get()
            if hreflang and href:
                languages[hreflang] = href
        return languages

    def get_current_date(self):
        return datetime.now().isoformat()