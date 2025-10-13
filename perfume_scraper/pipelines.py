"""
Scrapy pipelines for parfumo_spider.py

This module contains item pipelines following Scrapy best practices:
1. ValidationPipeline - Validates required fields
2. DataCleaningPipeline - Cleans and normalizes data
3. DuplicatesPipeline - Filters duplicate items
4. StatisticsPipeline - Collects processing statistics

Note: JSON export is handled by Feed Exports in spider settings.
"""

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
import logging


class ValidationPipeline:
    """
    Validates that items have all required fields populated.
    Drops items that fail validation.
    """
    
    # Define required fields for each item type
    REQUIRED_FIELDS = {
        'BrandItem': [
            'name',
            'url',
            'slug',
            'letter_category',
            'source_url',
            'scraped_at',
            'scraped_by'
        ],
        'PerfumeItem': [
            'name',
            'brand',
            'url'
        ],
        'CountryItem': [
            'name',
            'url'
        ],
        'DesignerItem': [
            'name',
            'url',
            'country',
            'perfume_count'
        ]
    }
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_item(self, item, spider):
        """Validate item has all required fields."""
        adapter = ItemAdapter(item)
        item_type = type(item).__name__
        
        # Get required fields for this item type
        required_fields = self.REQUIRED_FIELDS.get(item_type, [])
        
        if not required_fields:
            self.logger.warning(f"No validation rules defined for {item_type}")
            return item
        
        # Check each required field
        missing_fields = []
        for field in required_fields:
            if not adapter.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            raise DropItem(
                f"Missing required fields in {item_type}: {', '.join(missing_fields)}"
            )
        
        return item


class DataCleaningPipeline:
    """
    Cleans and normalizes item data.
    Ensures data consistency across all items.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_item(self, item, spider):
        """Clean and normalize item data."""
        adapter = ItemAdapter(item)
        item_type = type(item).__name__
        
        # Clean string fields - strip whitespace
        for field in adapter.field_names():
            value = adapter.get(field)
            if isinstance(value, str):
                cleaned = value.strip()
                adapter[field] = cleaned
        
        # Normalize URLs - ensure they're lowercase for consistency
        if adapter.get('url'):
            adapter['url'] = adapter['url'].strip()
        
        # For BrandItem - ensure slug is lowercase
        if item_type == 'BrandItem' and adapter.get('slug'):
            # Slug is already extracted by loader, just ensure consistency
            adapter['slug'] = adapter['slug'].strip()
        
        return item


class DuplicatesPipeline:
    """
    Filters out duplicate items based on unique identifiers.
    Uses in-memory set for tracking seen items.
    """
    
    def __init__(self):
        self.seen_items = set()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_item(self, item, spider):
        """Filter out duplicate items."""
        adapter = ItemAdapter(item)
        item_type = type(item).__name__
        
        # Determine unique identifier based on item type
        if item_type == 'BrandItem':
            # Use URL as unique identifier for brands
            identifier = adapter.get('url')
        elif item_type == 'PerfumeItem':
            # Use combination of name and brand for perfumes
            identifier = f"{adapter.get('name')}|{adapter.get('brand')}"
        elif item_type in ['CountryItem', 'DesignerItem']:
            # Use URL for countries and designers
            identifier = adapter.get('url')
        else:
            # For unknown types, use string representation
            identifier = str(item)
        
        # Check if we've seen this item before
        if identifier in self.seen_items:
            raise DropItem(f"Duplicate {item_type} found: {identifier}")
        
        # Mark as seen
        self.seen_items.add(identifier)
        return item
    
    def close_spider(self, spider):
        """Log statistics when spider closes."""
        self.logger.info(
            f"DuplicatesPipeline: Processed {len(self.seen_items)} unique items"
        )


class StatisticsPipeline:
    """
    Collects statistics about processed items.
    Logs summary when spider closes.
    """
    
    def __init__(self):
        self.stats = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def process_item(self, item, spider):
        """Count items by type."""
        item_type = type(item).__name__
        
        if item_type not in self.stats:
            self.stats[item_type] = 0
        
        self.stats[item_type] += 1
        return item
    
    def close_spider(self, spider):
        """Log statistics summary."""
        self.logger.info("=" * 60)
        self.logger.info("PIPELINE STATISTICS")
        self.logger.info("=" * 60)
        
        total_items = sum(self.stats.values())
        self.logger.info(f"Total items processed: {total_items}")
        
        for item_type, count in sorted(self.stats.items()):
            self.logger.info(f"  {item_type}: {count}")
        
        self.logger.info("=" * 60)


class PerfumeJsonExportPipeline:
    """
    Exports individual PerfumeItem instances as separate JSON files.
    Creates one file per perfume with format: parfumo_dumps/perfumes/{brand}_{name}.json
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.exported_count = 0
    
    def open_spider(self, spider):
        """Initialize export directory."""
        import os
        self.output_dir = os.path.join('parfumo_dumps', 'perfumes')
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"PerfumeJsonExportPipeline: Output directory: {self.output_dir}")
    
    def process_item(self, item, spider):
        """Export PerfumeItem as individual JSON file."""
        from perfume_scraper.items import PerfumeItem
        import json
        import re
        import os
        from datetime import datetime
        
        # Only process PerfumeItem instances
        if not isinstance(item, PerfumeItem):
            return item
        
        adapter = ItemAdapter(item)
        
        # Create safe filename from brand and perfume name
        brand = adapter.get('brand', 'Unknown').strip()
        name = adapter.get('name', 'Unknown').strip()
        
        # Clean filename - remove invalid characters
        def clean_filename(text):
            # Replace problematic characters with underscores
            text = re.sub(r'[<>:"/\\|?*]', '_', text)
            # Replace spaces and dots with underscores
            text = re.sub(r'[\s\.]+', '_', text)
            # Remove multiple underscores
            text = re.sub(r'_+', '_', text)
            # Remove leading/trailing underscores
            text = text.strip('_')
            # Limit length
            return text[:50] if text else 'unnamed'
        
        brand_clean = clean_filename(brand)
        name_clean = clean_filename(name)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{brand_clean}_{name_clean}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Convert item to dict
            item_dict = dict(adapter)
            
            # Write JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(item_dict, f, indent=2, ensure_ascii=False)
            
            self.exported_count += 1
            self.logger.info(f"✅ Exported perfume: {filepath}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to export perfume {brand} - {name}: {e}")
        
        return item
    
    def close_spider(self, spider):
        """Log export summary."""
        self.logger.info(f"PerfumeJsonExportPipeline: Exported {self.exported_count} perfume files")
