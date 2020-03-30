# -*- coding: utf-8 -*-
import scrapy
from scrapy.loader import ItemLoader
from avito.items import AvitoRealEstateItem


class AvitoSpider(scrapy.Spider):
    name = 'avito_blog'
    allowed_domains = ['avito.ru']
    start_urls = ['https://www.avito.ru/rossiya/kvartiry/']
    START_URL = 'https://www.avito.ru/rossiya/kvartiry/?p='

    def parse(self, response):
        pages_num = []
        for num in response.xpath("//div[contains(@class, 'js-pages')] //span/text()").extract():
            try:
                pages_num.append(f'{self.START_URL}{int(num)}')
            except TypeError:
                continue
            except ValueError:
                continue

        for page_url in pages_num:
            yield response.follow(page_url, callback=self.parse)
            for ads_url in response.xpath("//a[@class='snippet-link'] /@href").extract():
                yield response.follow(ads_url, callback=self.ads_parse)

    def ads_parse(self, response):
        item = ItemLoader(AvitoRealEstateItem(), response)
        item.add_xpath('title', "//span[@class='title-info-title-text']/text()")
        item.add_value('url', response.url)
        item.add_xpath('date', "//div[@class='title-info-metadata-item-redesign']/text()")


        parameters_list = []
        label_list = response.xpath("//li[@class='item-params-list-item']/span/text()").extract()
        value_list = response.xpath("//li[@class='item-params-list-item']//text()[2]").extract()

        item.add_xpath('photos', "//div[contains(@class, 'js-gallery-img-frame')] /@data-url")
        for k in range(len(label_list)):
            parameters_list.append(f'{label_list[k]}{value_list[k]}')
        item.add_value('parameters', parameters_list)
        yield item.load_item()
