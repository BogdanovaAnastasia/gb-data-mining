# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader.processors import MapCompose, TakeFirst
from datetime import date, timedelta


def clean_photo(values):
    if values[:2] == "//":
        return f'http:{values}'
    return values


def get_date(date_time):
    if date_time:
        date_time = date_time.strip()
        date_index = date_time.find(' в')
        ads_date = date_time[:date_index] if date_index >= 0 else date_time
        if ads_date == 'вчера':
            ads_date = (date.today() - timedelta(days=1)).strftime("%d.%m.%Y")
        if ads_date == 'сегодня':
            ads_date = date.today().strftime("%d.%m.%Y")
        return ads_date


class AvitoRealEstateItem(scrapy.Item):
    _id = scrapy.Field()
    title = scrapy.Field(output_processor=TakeFirst())
    url = scrapy.Field(output_processor=TakeFirst())
    date = scrapy.Field(input_processor=MapCompose(get_date), output_processor=TakeFirst())
    photos = scrapy.Field(input_processor=MapCompose(clean_photo))
    parameters = scrapy.Field()
