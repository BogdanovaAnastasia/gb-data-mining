# Сделать структуру файловых документов: собрать статьи по тегам,
# собрать информацию о каждой статье в отдельный файл, ресурс https://geekbrains.ru/posts

import json
import time
from typing import Dict, List, Union

import requests
from bs4 import BeautifulSoup

URL = 'https://geekbrains.ru/posts'
BASE_URL = 'https://geekbrains.ru'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'}

tag_dict: Dict[str, Dict[str, Union[str, List[str]]]] = {}


def get_next_page(soup: BeautifulSoup) -> str:
    ul = soup.find('ul', attrs={'class': 'gb__pagination'})
    a = ul.find(lambda tag: tag.name == 'a' and tag.text == '›')
    return f"{BASE_URL}{a['href']}" if a else None


def get_page(url):
    while url:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'lxml')
        yield soup
        time.sleep(1)
        url = get_next_page(soup)


def get_post_url(soup):
    post_a = soup.select('div.post-items-wrapper div.post-item a.post-item__title ')
    return set(f"{BASE_URL}{itm['href']}" for itm in post_a)


def get_post_data(post_url):
    template_data = {
        'url': '',
        'image': '',
        'title': '',
        'subtitle': '',
        'date': '',
        'author': {'name': '',
                   'url': ''
                   },
        'tags': []
    }
    response = requests.get(post_url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')
    template_data['url'] = post_url
    for_image = soup.select_one('article div.blogpost-content p img')
    template_data['image'] = for_image['src'] if for_image else None
    template_data['title'] = soup.select_one('article h1.blogpost-title').text
    template_data['subtitle'] = soup.select_one('article div.blogpost-description span').text
    template_data['date'] = soup.select_one('article div.blogpost-date-views time').text
    for_author_url = soup.select_one('div.avatar').parent
    template_data['author'] = {
        'name': soup.find('div', attrs={'itemprop': 'author'}).text,
        'url': f"{BASE_URL}{for_author_url['href']}" if for_author_url else None
    }

    for itm in soup.select('a.small'):
        tag = itm.text.replace(" ", "_")
        tag_url = f"{BASE_URL}{itm['href']}"
        template_data['tags'].append({tag: tag_url})
        if tag is not None:
            form_tag_data(tag, tag_url, post_url)
    return template_data


def form_tag_data(tag, tag_url, post_url):
    if tag_dict.get(tag):
        tag_dict[tag]['posts'].append(post_url)
    else:
        tag_dict[tag] = {'url': tag_url, 'posts': [post_url]}


def write_to_file(file_name, content):
    if len(content) != 0:
        if '/' in file_name:
            file_name = file_name.replace('/', '_')
        if ':' in file_name:
            file_name = file_name.replace(':', '')
        if '.' in file_name:
            file_name = file_name.replace('.', '-')
        with open(f'{file_name}.json', 'w') as file:
            file.write(json.dumps(content))
        print(f'Created file "{file_name}"')


if __name__ == '__main__':
    for soup in get_page(URL):
        posts = get_post_url(soup)
        for url in posts:
            data = get_post_data(url)
            write_to_file(data.get('url'), data)

    write_to_file('tags', tag_dict)
