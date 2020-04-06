import os
from pathlib import Path
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from blogparse.spiders.instagram import InstagramSpider
from blogparse import settings

env_path = Path(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

if __name__ == '__main__':
    craw_settings = Settings()
    craw_settings.setmodule(settings)
    crawler_proc = CrawlerProcess(settings=craw_settings)
    crawler_proc.crawl(InstagramSpider, logpass=(os.getenv('LOGIN'), os.getenv('PSWD')))
    crawler_proc.start()
