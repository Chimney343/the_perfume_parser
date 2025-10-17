"""
Scrapy Items for Parfumo scraper.

This module defines structured data containers for different types
of scraped data from parfumo.com.
"""

import scrapy
from datetime import datetime


class BrandItem(scrapy.Item):
    """
    Item representing a perfume brand from Parfumo.com.
    
    Fields:
        name (str): Brand name as displayed on Parfumo
        url (str): Full URL to the brand's perfume collection page
        slug (str): URL-friendly brand identifier (extracted from URL)
        letter_category (str): Letter category (0, A-Z) where brand was found
        source_url (str): URL of the page where brand was scraped from
        scraped_at (datetime): Timestamp when brand was scraped
        scraped_by (str): Spider name that scraped this brand
    """
    
    # Core fields
    name = scrapy.Field()
    url = scrapy.Field()
    
    # Derived/metadata fields
    slug = scrapy.Field()
    letter_category = scrapy.Field()
    source_url = scrapy.Field()
    
    # Tracking fields
    scraped_at = scrapy.Field()
    scraped_by = scrapy.Field()
    
    # Future fields (for when you scrape brand detail pages)
    country = scrapy.Field()  # Brand country of origin
    perfume_count = scrapy.Field()  # Number of perfumes
    description = scrapy.Field()  # Brand description
    year_founded = scrapy.Field()  # When brand was founded
    website = scrapy.Field()  # Official brand website


class BrandPageItem(scrapy.Item):
    """
    Item representing scraped data from a brand's perfume collection page.
    
    This item aggregates all perfume URLs found across paginated brand pages.
    
    Fields:
        brand_name (str): Name of the brand
        brand_url (str): Base URL to the brand's perfume collection
        perfume_urls (list): List of all perfume URLs found across all pages
        total_perfumes (int): Total number of perfumes (from pagination text)
        pages_scraped (int): Number of pagination pages processed
        scraped_at (datetime): Timestamp when scraping completed
        scraped_by (str): Spider name that scraped this data
    """
    
    # Core fields
    brand_name = scrapy.Field()
    brand_url = scrapy.Field()
    perfume_urls = scrapy.Field()  # List of URLs
    
    # Statistics
    total_perfumes = scrapy.Field()  # From "1 - 20 by 78" text
    pages_scraped = scrapy.Field()
    
    # Metadata
    scraped_at = scrapy.Field()
    scraped_by = scrapy.Field()
    
    # Additional field for country of origin
    country = scrapy.Field()  # Country of origin for the brand
    
    # Established year
    established = scrapy.Field()  # Year the brand was established
    
    # Brand description
    description = scrapy.Field()  # Full brand description text


class PerfumeItem(scrapy.Item):
    """
    Item representing an individual perfume with detailed information.
    
    Based on Parfumo perfume page structure containing:
    - Main accords
    - Fragrance pyramid (top/heart/base notes)
    - Perfumer info
    - Ratings (scent, longevity, sillage, bottle)
    """
    
    # Basic info
    name = scrapy.Field()
    brand = scrapy.Field()
    url = scrapy.Field()
    
    # Perfumer
    perfumer = scrapy.Field()
    perfumer_url = scrapy.Field()
    
    # Description
    description = scrapy.Field()
    gender = scrapy.Field()  # e.g., "women and men"
    
    # Main Accords (list of dicts with 'name' and 'intensity')
    main_accords = scrapy.Field()
    
    # Fragrance Pyramid Notes
    top_notes = scrapy.Field()      # List of note names
    heart_notes = scrapy.Field()    # List of note names  
    base_notes = scrapy.Field()     # List of note names
    
    # Ratings (each contains 'score' and 'votes')
    rating_scent = scrapy.Field()
    rating_longevity = scrapy.Field()
    rating_sillage = scrapy.Field()
    rating_bottle = scrapy.Field()
    
    # Overall/General Rating (aggregate rating from all categories)
    rating_overall = scrapy.Field()     # Overall rating score (e.g., "8.4")
    rating_count = scrapy.Field()       # Total number of ratings (e.g., "12")
    
    # Charts/Classification data (community classification)
    chart_type = scrapy.Field()         # Type classification (e.g., {"EDT": "45%", "EDP": "30%", ...})
    chart_style = scrapy.Field()        # Style classification (e.g., {"Fresh": "60%", "Oriental": "40%", ...})
    chart_season = scrapy.Field()       # Season classification (e.g., {"Spring": "40%", "Summer": "60%", ...})
    chart_occasion = scrapy.Field()     # Occasion classification (e.g., {"Daily": "70%", "Evening": "30%", ...})
    
    # Metadata
    scraped_at = scrapy.Field()
    scraped_by = scrapy.Field()


# Keep existing items for compatibility with other spiders
class CountryItem(scrapy.Item):
    """Item for country data from Fragrantica."""
    name = scrapy.Field()
    url = scrapy.Field()


class DesignerItem(scrapy.Item):
    """Item for designer/brand data from Fragrantica."""
    country = scrapy.Field()
    name = scrapy.Field()
    url = scrapy.Field()
    perfume_count = scrapy.Field()
