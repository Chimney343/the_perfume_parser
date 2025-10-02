from scrapy import signals
from scrapy.http import HtmlResponse
import random
import time


class PerfumeScraperSpiderMiddleware:
    '''Spider middleware for perfume scraper'''

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    def process_start_requests(self, start_requests, spider):
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class PerfumeScraperDownloaderMiddleware:
    '''Downloader middleware for perfume scraper'''

    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        ]

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Rotate user agents
        request.headers['User-Agent'] = random.choice(self.user_agents)

        # Add random delay
        time.sleep(random.uniform(0.5, 2.0))

        return None

    def process_response(self, request, response, spider):
        # Log successful responses
        if response.status == 200:
            spider.logger.info(f'Successfully scraped: {request.url}')
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.error(f'Error scraping {request.url}: {exception}')
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class ProxyRotationMiddleware:
    '''Middleware for proxy rotation (if needed)'''

    def __init__(self):
        self.proxies = [
            # Add proxy servers here if needed
            # 'http://proxy1:port',
            # 'http://proxy2:port',
        ]
        self.proxy_index = 0

    def process_request(self, request, spider):
        if self.proxies:
            proxy = self.proxies[self.proxy_index]
            request.meta['proxy'] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return None