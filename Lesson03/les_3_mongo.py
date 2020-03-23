# Источник https://habr.com/ru/
# задача:
# Обойти ленту популярного за неделю, сохранить данные в базы данных (Mongo, SQL)
# необходимые данные:
# - Загаловок статьи
# - Url статьи
# - количество комментариев в статье
# - дата и время публикации
# - автор (название и url)
# - авторы комментариев (название и url)
# для Mongo:
# создать коллекцию и все можно хранить в одной коллекции
# для SQL
# создать дополнительную таблицу для автора и автора комментариев и наладить связи

import time

import requests
from bs4 import BeautifulSoup

from pymongo import MongoClient

URL = 'https://habr.com/ru/top/weekly/'
BASE_URL = 'https://habr.com'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'}


def get_next_page(soup: BeautifulSoup) -> str:
    a = soup.find('a', attrs={'id': 'next_page'})
    return f"{BASE_URL}{a['href']}" if a else None


def get_page(url):
    while url:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        yield soup
        time.sleep(1)
        url = get_next_page(soup)


def get_post_url(soup):
    post_a = soup.select('h2.post__title a.post__title_link')
    return set(f"{itm['href']}" for itm in post_a)


def get_post_data(post_url):
    template_data = {
        'title': '',
        'url': '',
        'comment_count': '',
        'date_time': '',
        'author': {'name': '',
                   'url': ''
                   },
        'comment_authors': []
    }
    # comment_authors: [{'name': '', 'url': ''}, ]
    response = requests.get(post_url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')
    template_data['title'] = soup.select_one('article h1.post__title span.post__title-text').text
    template_data['url'] = post_url
    template_data['comment_count'] = soup.find('span', attrs={'id': 'comments_count'}).text.strip()
    template_data['date_time'] = soup.select_one('article div.post__wrapper span.post__time').text
    for_author = soup.find('a', attrs={'title': 'Автор публикации'})
    template_data['author'] = {
        'name': for_author.span.text.strip(),
        'url': f"{for_author['href']}" if for_author else None
    }
    for itm in set(soup.select('ul#comments-list a span.user-info__nickname_comment')):
        comment_user_name = itm.text
        comment_user_name_url = f"{itm.parent['href']}" if for_author else None
        template_data['comment_authors'].append({comment_user_name: comment_user_name_url})
    return template_data


if __name__ == '__main__':
    client = MongoClient('mongodb://localhost:27017/')
    db = client['habr_week_top']

    for soup in get_page(URL):
        posts = get_post_url(soup)
        data = [get_post_data(url) for url in posts]
        db['posts'].insert_many(data)
