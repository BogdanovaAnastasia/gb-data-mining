# Реализация функции разделения товаров на сайте 5ka.ru по категориям, запись товаров каждой категории в отдельный файл.
import requests
import time
import json

URL = 'https://5ka.ru/api/v2/special_offers/'
CAT_URL = 'https://5ka.ru/api/v2/categories/'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'}


def get_products(url, params=None):
    result = []
    while url:
        response = requests.get(url, headers=headers, params=params) if params else requests.get(url, headers=headers)
        params = None
        data = response.json()
        result.extend(data.get('results'))
        url = data.get('next')
        time.sleep(1)
    return result


def write_files(url):
    response = requests.get(url, headers=headers)
    categories = response.json()
    for category in categories:
        data = get_products(URL, {'categories': category.get('parent_group_code'), 'records_per_page': 20})
        if len(data) != 0:
            category_name = str(category.get('parent_group_name'))
            if '*\n*' in category_name:
                category_name = category_name.replace('*\n*', '.')
            if '"' in category_name:
                category_name = category_name.replace('"', '')
            file_name = f'{category_name}.json'
            with open(file_name, 'w') as file:
                file.write(json.dumps(data))
            print(f'Created file "{category_name}"')


if __name__ == '__main__':
    write_files(CAT_URL)
