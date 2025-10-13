"""
Item Loaders for Parfumo scraper.

ItemLoaders handle data extraction and cleaning with input/output processors.
"""

from itemloaders.processors import (
    TakeFirst, 
    MapCompose, 
    Join,
    Identity,
)
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re


# ============================================================
# CUSTOM PROCESSORS
# ============================================================

def clean_text(value):
    """
    Clean text by stripping whitespace and removing extra spaces.
    
    Args:
        value: Input text
        
    Returns:
        Cleaned text
    """
    if not value:
        return value
    
    # Strip whitespace
    value = value.strip()
    
    # Remove extra whitespace
    value = re.sub(r'\s+', ' ', value)
    
    return value


def normalize_brand_name(value):
    """
    Normalize brand name.
    
    Args:
        value: Brand name
        
    Returns:
        Normalized brand name
    """
    if not value:
        return value
    
    value = clean_text(value)
    
    # Remove trailing punctuation
    value = value.rstrip('.,;:')
    
    return value


def extract_slug_from_url(url):
    """
    Extract the brand slug from a Parfumo URL.
    
    Args:
        url: Full brand URL (e.g., https://www.parfumo.com/Perfumes/brand-name)
        
    Returns:
        Brand slug (e.g., 'brand-name')
    """
    if not url:
        return None
    
    try:
        path = urlparse(url).path
        # Extract last part of path
        slug = path.rstrip('/').split('/')[-1]
        return slug if slug else None
    except Exception:
        return None


def clean_number(value):
    """
    Extract numeric value from string.
    
    Args:
        value: String containing number
        
    Returns:
        Integer or None
    """
    if not value:
        return None
    
    # Extract digits
    digits = re.sub(r'\D', '', str(value))
    
    try:
        return int(digits) if digits else None
    except ValueError:
        return None


# ============================================================
# ITEM LOADERS
# ============================================================

class BrandItemLoader(ItemLoader):
    """
    ItemLoader for BrandItem with custom processors.
    
    This loader handles the extraction and cleaning of brand data
    from Parfumo brand list pages.
    """
    
    default_input_processor = MapCompose(remove_tags, clean_text)
    default_output_processor = TakeFirst()
    
    # Core fields
    name_in = MapCompose(remove_tags, normalize_brand_name)
    name_out = TakeFirst()
    
    url_in = MapCompose(str.strip)
    url_out = TakeFirst()
    
    # Derived fields
    slug_in = MapCompose(extract_slug_from_url)
    slug_out = TakeFirst()
    
    letter_category_in = MapCompose(str.strip, str.upper)
    letter_category_out = TakeFirst()
    
    source_url_in = MapCompose(str.strip)
    source_url_out = TakeFirst()
    
    # Metadata fields
    scraped_at_out = TakeFirst()
    scraped_by_out = TakeFirst()
    
    # Future fields
    country_in = MapCompose(remove_tags, clean_text)
    country_out = TakeFirst()
    
    perfume_count_in = MapCompose(clean_number)
    perfume_count_out = TakeFirst()
    
    description_in = MapCompose(remove_tags, clean_text)
    description_out = Join(' ')
    
    year_founded_in = MapCompose(clean_number)
    year_founded_out = TakeFirst()
    
    website_in = MapCompose(str.strip)
    website_out = TakeFirst()


class PerfumeItemLoader(ItemLoader):
    """
    ItemLoader for PerfumeItem (for future use).
    
    This loader handles the extraction and cleaning of perfume data
    from individual perfume detail pages.
    """
    
    default_input_processor = MapCompose(remove_tags, clean_text)
    default_output_processor = TakeFirst()
    
    # Lists of notes
    top_notes_in = MapCompose(remove_tags, clean_text)
    top_notes_out = Identity()  # Keep as list
    
    middle_notes_in = MapCompose(remove_tags, clean_text)
    middle_notes_out = Identity()  # Keep as list
    
    base_notes_in = MapCompose(remove_tags, clean_text)
    base_notes_out = Identity()  # Keep as list
    
    # Numbers
    year_in = MapCompose(clean_number)
    year_out = TakeFirst()
    
    votes_in = MapCompose(clean_number)
    votes_out = TakeFirst()
    
    # Text fields
    description_in = MapCompose(remove_tags, clean_text)
    description_out = Join(' ')

class BrandPageItemLoader(ItemLoader):
    """
    ItemLoader for BrandPageItem with custom processors.

    This loader handles the extraction and cleaning of brand page data
    from Parfumo brand pages.
    """

    default_input_processor = MapCompose(remove_tags, clean_text)
    default_output_processor = TakeFirst()

    # Core fields
    brand_name_in = MapCompose(remove_tags, normalize_brand_name)
    brand_name_out = TakeFirst()

    brand_url_in = MapCompose(str.strip)
    brand_url_out = TakeFirst()

    perfume_urls_in = Identity()  # Keep as list
    perfume_urls_out = Identity()

    pages_scraped_in = MapCompose(clean_number)
    pages_scraped_out = TakeFirst()

    total_perfumes_in = MapCompose(clean_number)
    total_perfumes_out = TakeFirst()

    # Metadata fields
    scraped_at_out = TakeFirst()
    scraped_by_out = TakeFirst()

    # Established year field
    established_in = MapCompose(
        remove_tags, 
        clean_text, 
        lambda x: re.search(r'\d{4}', x).group() if re.search(r'\d{4}', x) else ('Unknown' if x.strip().lower() == 'unknown' else None)
    )
    established_out = TakeFirst()
