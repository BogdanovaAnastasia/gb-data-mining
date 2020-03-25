# -*- coding: utf-8 -*-
import scrapy
from datetime import date, timedelta


def _get_date(response) -> str:
    date_time = response.xpath(
        "//article //div[@class='post__wrapper'] //span[@class='post__time']/text()").extract_first()
    date_index = date_time.find(' в')
    art_date = date_time[:date_index] if date_index >= 0 else date_time
    if art_date == 'вчера':
        art_date = (date.today() - timedelta(days=1)).strftime("%d.%m.%Y")
    if art_date == 'сегодня':
        art_date = date.today().strftime("%d.%m.%Y")
    return art_date


class HabrBlogSpider(scrapy.Spider):
    name = 'habr_blog'
    allowed_domains = ['habr.com']
    start_urls = ['https://habr.com/ru/top/weekly/']

    def parse(self, response):
        pagination_urls = response.xpath("//div[@class='page__footer'] //li /a /@href").extract()
        for itm in pagination_urls:
            yield response.follow(itm, callback=self.parse)

        for post_url in response.xpath("//h2[@class='post__title'] /a[@class='post__title_link'] /@href"):
            yield response.follow(post_url, callback=self.post_parse)

    def post_parse(self, response):
        data = {
            'title': response.xpath("//article //h1 /span[@class='post__title-text']/text()").extract_first(),
            'url': response.url,
            'author': {
                'name': response.xpath("//a[@title='Автор публикации'] //span[contains(@class, 'user-info__nickname')]/text()").extract_first().strip(),
                'url': response.xpath("//a[@title='Автор публикации'] /@href").extract_first(),
            },
            'tags': response.xpath("//dd[@class='post__tags-list'] /ul[contains(@class, 'js-post-tags')] /li /a/text()").extract(),
            'hubs': list(map(lambda hub: hub.strip(), response.xpath("//dd[@class='post__tags-list'] /ul[contains(@class, 'js-post-hubs')] /li /a/text()").extract())),
            'date': _get_date(response),
            'comment_count': response.xpath("//span[@id='comments_count']/text()").extract_first().strip(),
            'parsing_date': date.today().strftime("%d.%m.%Y")
        }
        yield data
