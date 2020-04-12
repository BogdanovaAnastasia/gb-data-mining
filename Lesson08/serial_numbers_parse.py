# -*- coding: utf-8 -*-
# Задача:
# Извлечь серийные номера из файлов ( приложены в материалах урока)
#
# Ваша задача разобрать все фалы, распознать на них серийный номер и создать коллекцию в MongoDB с четким указанием из
# какого файла был взят тот или иной серийный номер.
#
# Дополнительно необходимо создать коллекцию и отдельную папку для хранения файлов в которых вы не смогли распознать
# серийный номер, если в файле встречается несколько изображений необходимо явно указать что в файле таком-то страница
# такая серийный номер не найден.

import PyPDF2
import pytesseract
import os
from pathlib import Path
from PIL import Image
from PyPDF2.utils import PdfReadError
from shutil import copyfile
from pymongo import MongoClient

# файлы для парсинга находятся в папке data_for_parse/СКД_Поверка весов

CURRENT_DIR = Path.cwd()
DIR_TO_PARSE = 'data_for_parse'
DIR_TO_FILES = 'СКД_Поверка весов'
DIR_TO_IMAGES = 'image'
DIR_TO_ERROR = 'error_files'

path_to_parse = Path.cwd() / DIR_TO_PARSE
files_to_parse_path = Path.cwd() / DIR_TO_PARSE / DIR_TO_FILES
image_folder_path = path_to_parse / DIR_TO_IMAGES
error_files_folder_path = path_to_parse / DIR_TO_ERROR

if not image_folder_path.exists():
    image_folder_path.mkdir()
if not error_files_folder_path.exists():
    error_files_folder_path.mkdir()

PATTERNS = ['заводской (серийный) номер', 'заводской номер (номера)']
ERROR_CAUSES = ['ERROR_EXTENSION', 'ERROR_FILE_READ', 'ERROR_FILE_NOT_EXIST', 'ERROR_FINDING_SERIAL_NUMBERS']


class FileItem:
    name: str
    file_path: str
    parse_path: str
    page: str = 'all pages'
    numbers: [str]
    error_cause: str

    def __init__(self, file_path, name):
        self.file_path = file_path
        self.name = name


def extract_pdf_image(pdf_path, error_col):
    result = []
    try:
        pdf_file = PyPDF2.PdfFileReader(
            open(pdf_path, 'rb'),
            strict=False
        )
        for page_num in range(0, pdf_file.getNumPages()):
            page = pdf_file.getPage(page_num)
            page_obj = page['/Resources']['/XObject'].getObject()
            key = list(page_obj.keys())[0]
            if page_obj[key].get('/Subtype') == '/Image':
                image = page_obj[key]
                size = (image['/Width'], image['/Height'])
                data = image._data
                mode = 'RGB' if image['/ColorSpace'] == '/DeviceRGB' else 'P'
                decoder = image['/Filter']
                if decoder == '/DCTDecode':
                    file_type = 'jpeg'
                elif decoder == '/FlateDecode':
                    file_type = 'png'
                elif decoder == '/JPXDecode':
                    file_type = 'jp2'
                else:
                    file_type = 'bmp'
                result_strict = {
                    'page': page_num,
                    'size': size,
                    'data': data,
                    'mode': mode,
                    'file_type': file_type,
                }
                result.append(result_strict)
    except PdfReadError as e:
        print(e)
        file = FileItem(pdf_path, get_name(pdf_path))
        file.error_cause = ERROR_CAUSES[1]
        put_file_in_error_dir(file, error_col)
    except FileNotFoundError as e:
        print(e)
        file = FileItem(pdf_path, get_name(pdf_path))
        file.error_cause = ERROR_CAUSES[2]
        put_file_in_error_dir(file, error_col)
    return result


def save_pdf_image(file_path, f_path, *pdf_strict):
    items = []

    for itm in pdf_strict:
        name = f'{get_name(file_path)}_#_{itm["page"]}.{itm["file_type"]}'
        img_path = os.path.join(f_path, name)
        with open(img_path, 'wb') as image:
            image.write(itm['data'])
        item = FileItem(file_path, get_name(file_path))
        item.parse_path = img_path
        item.page = itm["page"]
        items.append(item)
    return items


def save_jpg_image(file_path, f_path):
    name = f'{get_name(file_path)}_#_0.{get_extension(file_path)}'
    new_file_path = os.path.join(f_path, name)
    copyfile(file_path, new_file_path)
    item = FileItem(file_path, get_name(file_path))
    item.parse_path = new_file_path
    item.page = '0'
    return item


def extract_number(item: FileItem, correct_col, error_col):
    file_path = item.parse_path
    numbers = []
    img_obj = Image.open(file_path)
    text = pytesseract.image_to_string(img_obj, 'rus')
    for idx, line in enumerate(text.split('\n')):
        if any(pattern in line.lower() for pattern in PATTERNS):
            offset = 0
            if PATTERNS[0] in line.lower():
                offset = len(PATTERNS[0]) + 1
            if PATTERNS[1] in line.lower():
                offset = len(PATTERNS[1]) + 1
            rus_num = find_longest(line[offset:]).replace('.', '')
            text_en = pytesseract.image_to_string(img_obj, 'eng')
            number = find_longest(text_en.split('\n')[idx][offset:]).replace('.', '')
            if text_en.lower().find(rus_num) + 1 and number != rus_num and len(rus_num) >= len(number):
                number = rus_num
            numbers.append(number)
    if not numbers:
        item.error_cause = ERROR_CAUSES[3]
        put_file_in_error_dir(item, error_col)
    else:
        item.numbers = numbers
        save_correct_file_to_db(item, correct_col)


def put_file_in_error_dir(item: FileItem, error_col):
    error_path = os.path.join(error_files_folder_path, get_name(item.file_path)[0])
    copyfile(item.file_path, error_path)
    error_data = make_item_from_error_template(item)
    try:
        error_col.insert_one(error_data)
    except Exception as e:
        print(e)


def save_correct_file_to_db(item: FileItem, correct_col):
    correct_data = make_item_from_serial_number_template(item)
    try:
        correct_col.insert_one(correct_data)
    except Exception as e:
        print(e)


def get_all_file_paths_from_dir(directory):
    files = []
    for file_or_dir in os.listdir(directory):
        file_or_dir = os.path.join(directory, file_or_dir)
        if os.path.isfile(file_or_dir):
            files.append(file_or_dir)
        if os.path.isdir(file_or_dir):
            files.extend(get_all_file_paths_from_dir(file_or_dir))
    return files


def get_name(file_path):
    return os.path.basename(Path(file_path))


def get_extension(file_path):
    return Path(file_path).suffix


def get_file_path_without_cwd(file_path):
    return file_path.replace(str(path_to_parse), '')


def find_longest(some_str):
    str_list = some_str.strip().lower().split(' ')
    ind = 0
    for s_ind in range(1, len(str_list)):
        if len(str_list[s_ind]) > len(str_list[ind]):
            ind = s_ind
    return str_list[ind]


def convert_files_to_convenient_format(file_paths, error_col):
    convenient_items = []
    for file_path in file_paths:
        extension = get_extension(file_path)
        if extension == '.pdf':
            pdf_data = extract_pdf_image(file_path, error_col)
            items = save_pdf_image(file_path, image_folder_path, *pdf_data)
            convenient_items.extend(items)
        elif extension == '.jpg':
            convenient_items.append(save_jpg_image(file_path, image_folder_path))
        else:
            item = FileItem(file_path, get_name(file_path))
            item.error_cause = ERROR_CAUSES[0]
            put_file_in_error_dir(item, error_col)
    return convenient_items


def make_item_from_error_template(item: FileItem):
    return {
        'name': item.name,
        'file_path': get_file_path_without_cwd(item.file_path),
        'page': item.page,
        'error_cause': item.error_cause
    }


def make_item_from_serial_number_template(item: FileItem):
    return {
        'name': item.name,
        'file_path': get_file_path_without_cwd(item.file_path),
        'page': item.page,
        'serial_numbers': item.numbers
    }


if __name__ == '__main__':
    client = MongoClient('mongodb://localhost:27017/')
    db = client['file_serials_parse']
    serial_numbers = db['serial_numbers']
    errors = db['errors']

    file_paths_to_parse = get_all_file_paths_from_dir(files_to_parse_path)
    items_to_parse = convert_files_to_convenient_format(file_paths_to_parse, errors)
    [extract_number(file, serial_numbers, errors) for file in items_to_parse]
