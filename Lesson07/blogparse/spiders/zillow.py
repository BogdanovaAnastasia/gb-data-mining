# -*- coding: utf-8 -*-
import scrapy
from scrapy.loader import ItemLoader
from blogparse.items import ZillowItem
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time


class ZillowSpider(scrapy.Spider):
    name = 'zillow'
    allowed_domains = ['zillow.com']
    start_urls = ['https://www.zillow.com/san-francisco-ca/']

    browser = webdriver.Firefox()

    def parse(self, response):
        for page_url in response.xpath("//nav[@aria-label='Pagination']/ul/li/a/@href").extract():
            yield response.follow(page_url, callback=self.parse)

            for ads_url in response.xpath("//ul[contains(@class,'photo-cards_short')]/li/article/div[@class='list-card-info']/a/@href").extract():
                yield response.follow(ads_url, callback=self.ads_parse)

    def ads_parse(self, response):
        self.browser.get(response.url)
        media_col = self.browser.find_element_by_css_selector('.ds-media-col')
        photo_pic_len = len(self.browser.find_elements_by_xpath('//ul[@class="media-stream"]/li//source[@type="image/jpeg"]'))
        while True:
            media_col.send_keys(Keys.PAGE_DOWN)
            media_col.send_keys(Keys.PAGE_DOWN)
            media_col.send_keys(Keys.PAGE_DOWN)
            media_col.send_keys(Keys.PAGE_DOWN)
            media_col.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.3)
            tmp = len(self.browser.find_elements_by_xpath('//ul[@class="media-stream"]/li//source[@type="image/jpeg"]'))
            if tmp == photo_pic_len:
                break
            photo_pic_len = tmp
        images = [itm.get_attribute('srcset').split(' ')[-2] for itm in self.browser.find_elements_by_xpath('//ul[@class="media-stream"]/li//source[@type="image/jpeg"]')]

        item = ItemLoader(ZillowItem(), response)
        item.add_xpath('title', "//title/text()")
        item.add_value('url', response.url)
        item.add_xpath('price', '//div[@class="ds-chip"]//span/span[@class="ds-value"]/text()')
        item.add_value('address', ''.join(response.xpath('//h1[@class="ds-address-container"]//text()').extract()).replace(u'\xa0', u' '))
        item.add_value('sqft', response.xpath('//header/h3/span[@class="ds-bed-bath-living-area"]/span/text()').extract()[-3])
        item.add_value('photos', images)

        yield item.load_item()
