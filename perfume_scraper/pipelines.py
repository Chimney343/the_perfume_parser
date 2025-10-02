import json
import csv
import re
import os
from datetime import datetime
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class ValidationPipeline:
    '''Pipeline to validate scraped data'''

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Validate required fields
        if not adapter.get('name'):
            raise DropItem(f"Missing perfume name: {item}")

        if not adapter.get('brand'):
            raise DropItem(f"Missing brand: {item}")

        # Validate ratings are within expected ranges
        ratings = adapter.get('ratings', {})
        if isinstance(ratings, dict):
            overall_rating = ratings.get('overall_rating')
            if overall_rating and (overall_rating < 0 or overall_rating > 5):
                spider.logger.warning(f"Invalid rating value: {overall_rating}")

        return item


class CleaningPipeline:
    '''Pipeline to clean and normalize data'''

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Clean text fields
        text_fields = ['name', 'brand', 'description', 'fragrance_family']
        for field in text_fields:
            value = adapter.get(field)
            if isinstance(value, str):
                # Remove extra whitespace and normalize
                cleaned = re.sub(r'\s+', ' ', value).strip()
                adapter[field] = cleaned

        # Normalize URLs
        url = adapter.get('url')
        if url and not url.startswith('http'):
            if url.startswith('//'):
                adapter['url'] = f"https:{url}"
            elif url.startswith('/'):
                adapter['url'] = f"https://www.fragrantica.com{url}"

        return item


class JsonExportPipeline:
    '''Pipeline to export data to JSON'''

    def __init__(self):
        self.items = []

    def process_item(self, item, spider):
        self.items.append(ItemAdapter(item).asdict())
        return item

    def close_spider(self, spider):
        # Create downloaded folder if it doesn't exist
        downloaded_dir = 'downloaded'
        os.makedirs(downloaded_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(downloaded_dir, f'perfume_data_{timestamp}.json')

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2, default=str)

        spider.logger.info(f"Exported {len(self.items)} items to {filename}")


class CsvExportPipeline:
    '''Pipeline to export flattened data to CSV'''

    def __init__(self):
        self.items = []

    def process_item(self, item, spider):
        self.items.append(ItemAdapter(item).asdict())
        return item

    def close_spider(self, spider):
        if not self.items:
            return

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'perfume_summary_{timestamp}.csv'

        # Define CSV fields
        fieldnames = [
            'name', 'brand', 'launch_year', 'gender', 'fragrance_family',
            'overall_rating', 'rating_count', 'review_count', 'longevity', 'sillage',
            'notes_pyramid', 'main_accord', 'url'
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for item in self.items:
                row = self._flatten_item(item)
                writer.writerow(row)

        spider.logger.info(f"Exported {len(self.items)} items to {filename}")

    def _flatten_item(self, item):
        '''Flatten complex item structure for CSV'''
        ratings = item.get('ratings', {})
        notes_pyramid = item.get('notes_pyramid', [])
        accords = item.get('main_accords', [])

        return {
            'name': item.get('name', ''),
            'brand': item.get('brand', ''),
            'launch_year': item.get('launch_year', ''),
            'gender': item.get('gender', ''),
            'fragrance_family': item.get('fragrance_family', ''),
            'overall_rating': ratings.get('overall_rating', ''),
            'rating_count': ratings.get('rating_count', ''),
            'review_count': ratings.get('review_count', ''),
            'longevity': ratings.get('longevity', ''),
            'sillage': ratings.get('sillage', ''),
            'notes_pyramid': ', '.join(notes_pyramid),
            'main_accord': accords[0]['name'] if accords else '',
            'url': item.get('url', '')
        }


class DatabasePipeline:
    '''Pipeline to save data to database (SQLite example)'''

    def __init__(self):
        self.connection = None
        self.cursor = None

    def open_spider(self, spider):
        import sqlite3
        self.connection = sqlite3.connect('perfumes.db')
        self.cursor = self.connection.cursor()

        # Create tables
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS perfumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                launch_year INTEGER,
                gender TEXT,
                fragrance_family TEXT,
                description TEXT,
                url TEXT UNIQUE,
                overall_rating REAL,
                rating_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fragrance_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                perfume_id INTEGER,
                note_name TEXT,
                note_type TEXT,
                FOREIGN KEY (perfume_id) REFERENCES perfumes (id)
            )
        ''')

        self.connection.commit()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Insert perfume data
        ratings = adapter.get('ratings', {})
        self.cursor.execute('''
            INSERT OR REPLACE INTO perfumes 
            (name, brand, launch_year, gender, fragrance_family, description, url, overall_rating, rating_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            adapter.get('name'),
            adapter.get('brand'),
            adapter.get('launch_year'),
            adapter.get('gender'),
            adapter.get('fragrance_family'),
            adapter.get('description'),
            adapter.get('url'),
            ratings.get('overall_rating'),
            ratings.get('rating_count')
        ))

        perfume_id = self.cursor.lastrowid

        # Insert pyramid links
        notes_pyramid = adapter.get('notes_pyramid', [])
        if isinstance(notes_pyramid, list):
            for link in notes_pyramid:
                self.cursor.execute('''
                    INSERT INTO notes_pyramid (perfume_id, note_link)
                    VALUES (?, ?)
                ''', (perfume_id, link))

        self.connection.commit()
        return item

    def close_spider(self, spider):
        if self.connection:
            self.connection.close()