import scrapy

class PerfumeItem(scrapy.Item):
    # Basic perfume information
    name = scrapy.Field()
    brand = scrapy.Field()
    launch_year = scrapy.Field()
    fragrance_id = scrapy.Field()
    perfumer = scrapy.Field()
    gender = scrapy.Field()
    fragrance_family = scrapy.Field()
    description = scrapy.Field()
    url = scrapy.Field()

    # Fragrance notes
    notes_pyramid = scrapy.Field()  # List of links to pyramid notes
    main_accords = scrapy.Field()  # List of dicts with name and intensity

    # Ratings and performance
    ratings = scrapy.Field()  # Dict with various rating metrics
    seasonal_performance = scrapy.Field()

    # Visual assets
    images = scrapy.Field()  # Dict with main_image, bottle_images, etc.

    # User reviews
    reviews = scrapy.Field()  # Dict with total_reviews and recent_reviews

    # Recommendations and related
    recommendations = scrapy.Field()  # Dict with similar_fragrances, etc.

    # Brand information
    brand_info = scrapy.Field()

    # Collections
    collections = scrapy.Field()

    # Availability and pricing
    availability = scrapy.Field()

    # Metadata
    metadata = scrapy.Field()


class ReviewItem(scrapy.Item):
    # Individual review data
    perfume_id = scrapy.Field()
    author = scrapy.Field()
    date = scrapy.Field()
    rating = scrapy.Field()
    text = scrapy.Field()
    votes = scrapy.Field()
    review_id = scrapy.Field()


class FragranceNoteItem(scrapy.Item):
    # Individual fragrance note
    name = scrapy.Field()
    category = scrapy.Field()  # top, middle, base
    perfume_id = scrapy.Field()


class AccordItem(scrapy.Item):
    # Individual accord with intensity
    name = scrapy.Field()
    intensity = scrapy.Field()
    perfume_id = scrapy.Field()