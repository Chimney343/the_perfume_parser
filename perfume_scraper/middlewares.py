from scrapy import signals
from scrapy.http import HtmlResponse
import random
import time
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem


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
        # Initialize random user agent generator
        software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value, SoftwareName.SAFARI.value]
        operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.MAC.value, OperatingSystem.LINUX.value]
        self.user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems)

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Rotate user agents using random-user-agent library
        user_agent = self.user_agent_rotator.get_random_user_agent()
        request.headers['User-Agent'] = user_agent

        # Log the selected user agent at debug level
        spider.logger.debug(f'Using User-Agent: {user_agent}')

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