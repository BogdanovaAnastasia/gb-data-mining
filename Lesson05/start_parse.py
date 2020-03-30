from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from avito.spiders.avito import AvitoSpider
from avito import settings

if __name__ == '__main__':
    craw_settings = Settings()
    craw_settings.setmodule(settings)
    crawler_proc = CrawlerProcess(settings=craw_settings)
    crawler_proc.crawl(AvitoSpider)
    crawler_proc.start()
