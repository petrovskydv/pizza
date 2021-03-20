import logging
import os
import time
from functools import wraps

import requests

logger = logging.getLogger(__name__)
_token = None
_headers = None


def validate_access_token(fnc):
    @wraps(fnc)
    def wrapped(*args, **kwargs):
        if _token['creation_time'] + _token['expires_in'] < time.time():
            logger.info('Срок действия токена истекает. Получаем новый токен')
            get_access_token()
            set_headers()
        res = fnc(*args, **kwargs)
        return res

    return wrapped


@validate_access_token
def get_all_products():
    logger.info('Получаем список товаров')
    response = requests.get('https://api.moltin.com/v2/products', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    products_for_menu = []
    for product in review_result['data']:
        product_for_menu = {
            'id': product['id'],
            'name': product['name'],
            'description': product['description'],
            'price': product['meta']['display_price']['with_tax']['formatted'],
            'image_id': product['relationships']['main_image']['data']['id']
        }
        products_for_menu.append(product_for_menu)
    return products_for_menu


@validate_access_token
def get_product(product_id):
    logger.info(f'Получаем товар с id {product_id}')
    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def create_product(product):
    logger.info(f'Создаем товар {product}')

    data = {
        'data': {
            'type': 'product',
            'name': product['name'],
            'slug': str(product['id']),
            'sku': product['name'],
            'manage_stock': False,
            'description': product['description'],
            'status': 'live',
            'commodity_type': 'physical',
            'price': [
                {
                    "amount": product['price'] * 100,
                    "currency": "RUB",
                    "includes_tax": True
                }
            ]
        }
    }

    response = requests.post('https://api.moltin.com/v2/products', headers=_headers, json=data)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']['id']


@validate_access_token
def create_file(image_file):
    logger.info(f'Загружаем файл {image_file[0]}')
    files = {'file': image_file}
    response = requests.post('https://api.moltin.com/v2/files', headers=_headers, files=files)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']['id']


def create_product_main_image(product_id, image_id):
    logger.info(f'Устанавливаем основную картинку товара {product_id}')
    data = {
        'data': {
            'id': image_id,
            'type': 'main_image'
        }
    }
    response = requests.post(f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image',
                             headers=_headers, json=data)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


def create_flow(flow_name, flow_description):
    logger.info(f'Создаем новый flow {flow_name}')
    data = {
        'data': {
            'type': 'flow',
            'name': flow_name,
            'slug': flow_name,
            'description': flow_description,
            'enabled': True
        }
    }
    response = requests.post('https://api.moltin.com/v2/flows', headers=_headers, json=data)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']['id']


def create_flow_field(flow_id, field):
    logger.info(f'Создаем поле {field} для flow_id {flow_id}')
    data = {
        'data': {
            'type': 'field',
            'name': field['name'],
            'slug': field['name'],
            'field_type': field['type'],
            'description': field['description'],
            'required': True,
            'enabled': True,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    }
                }
            }
        }
    }
    response = requests.post('https://api.moltin.com/v2/fields', headers=_headers, json=data)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']['id']


def create_flow_entry(flow_slug, fields):
    logger.info(f'Создаем новую запись {fields} в {flow_slug}')
    data = {
        'data': {
            'type': 'entry'
        }
    }
    for field_name, field_value in fields.items():
        data['data'][field_name] = field_value

    response = requests.post(f'https://api.moltin.com/v2/flows/{flow_slug}/entries', headers=_headers, json=data)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']['id']


@validate_access_token
def get_all_entries(flow_slug, url=None):
    logger.info(f'Получаем все элементы списка {flow_slug}')
    entries_per_page_number = 50
    params = {
        'page[limit]': entries_per_page_number
    }
    if not url:
        url = f'https://api.moltin.com/v2/flows/{flow_slug}/entries'
    response = requests.get(url, headers=_headers, params=params)
    response.raise_for_status()
    review_result = response.json()
    entries = review_result['data']
    page = review_result['meta']['page']
    next_page = review_result['links']['next']
    if page['current'] != page['total']:
        next_entries = get_all_entries(flow_slug, next_page)
        entries.extend(next_entries)
    return entries


@validate_access_token
def get_entry(flow_slug, entry_id):
    logger.info(f'Получаем элемент списка {flow_slug} с id {entry_id}')
    response = requests.get(f'https://api.moltin.com/v2/flows/{flow_slug}/entries/{entry_id}', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def get_file_href(file_id):
    logger.info(f'Получаем ссылку основного изображения товара с id {file_id}')
    response = requests.get(f'https://api.moltin.com/v2/files/{file_id}', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']['link']['href']


@validate_access_token
def add_product_to_cart(reference, product_id, quantity):
    headers = {**_headers, 'Content-Type': 'application/json'}

    data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity
        }
    }
    logger.info(f'Добавляем товар с id {product_id} в количестве {quantity} в корзину {reference}')
    response = requests.post(f'https://api.moltin.com/v2/carts/{reference}/items/', headers=headers, json=data)
    response.raise_for_status()


@validate_access_token
def remove_product_from_cart(reference, product_id):
    logger.info(f'Удаляем товар с id {product_id} из корзины {reference}')
    response = requests.delete(f'https://api.moltin.com/v2/carts/{reference}/items/{product_id}', headers=_headers)
    response.raise_for_status()


@validate_access_token
def get_cart(reference):
    logger.info(f'Получаем данные корзины {reference}')
    response = requests.get(f'https://api.moltin.com/v2/carts/{reference}', headers=_headers)
    response.raise_for_status()
    return response.json()


@validate_access_token
def get_cart_items(reference):
    logger.info(f'Получаем товары корзины {reference}')
    response = requests.get(f'https://api.moltin.com/v2/carts/{reference}/items', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def create_customer(customer_name, customer_email):
    data = {
        'data': {
            'type': 'customer',
            'name': customer_name,
            'email': customer_email
        }
    }
    logger.info(f'Создаем покупателя {customer_name}, email: {customer_email}')
    response = requests.post('https://api.moltin.com/v2/customers', headers=_headers, json=data)
    response.raise_for_status()


def get_access_token():
    logger.info('Получаем токен')
    payload = {
        'client_id': os.environ['STORE_CLIENT_ID'],
        'client_secret': os.environ['STORE_CLIENT_SECRET'],
        'grant_type': 'client_credentials'
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=payload)
    response.raise_for_status()
    review_result = response.json()

    global _token
    _token = review_result
    _token['expires_in'] = _token['expires_in'] - 10
    _token['creation_time'] = time.time()


def set_headers():
    global _headers
    _headers = {'Authorization': f'Bearer {_token["access_token"]}'}
