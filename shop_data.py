import json
import logging
import os
import sys

import requests
import urllib3
from dotenv import load_dotenv

import online_shop

logger = logging.getLogger(__name__)


def open_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as my_file:
        return json.load(my_file)


def download_image(file_name, url):
    response = requests.get(url, verify=False)
    response.raise_for_status()
    return [file_name, response.content]


def create_products(file_path):
    products = open_json_file(file_path)
    for product in products:
        try:
            product_id = online_shop.create_product(product)
            image_file = download_image(f"{product['name']}.jpg", product['product_image']['url'])
            image_id = online_shop.create_file(image_file)
            online_shop.create_product_main_image(product_id, image_id)
        except requests.HTTPError as e:
            print(e.response.text, file=sys.stderr)
            logger.exception(e)
        except requests.ConnectionError as e:
            logger.exception(e)
            print(e.response.text, file=sys.stderr)


def create_flow(flow, field_names, field_descriptions):
    try:
        flow_id = online_shop.create_flow(flow['name'], flow['description'])
        for field_description in field_descriptions:
            field = dict(zip(field_names, field_description))
            online_shop.create_flow_field(flow_id, field)
    except requests.HTTPError as e:
        print(e.response.text, file=sys.stderr)
        logger.exception(e)
    except requests.ConnectionError as e:
        logger.exception(e)
        print(e.response.text, file=sys.stderr)


def fill_pizzeria_addresses(file_path):
    pizzerias = open_json_file(file_path)
    for pizzeria in pizzerias:
        fields = {
            'Alias': pizzeria['alias'],
            'Address': pizzeria['address']['full'],
            'Longitude': pizzeria['coordinates']['lon'],
            'Latitude': pizzeria['coordinates']['lat']
        }
        try:
            online_shop.create_flow_entry('Pizzeria', fields)
        except requests.HTTPError as e:
            print(e.response.text, file=sys.stderr)
            logger.exception(e)
        except requests.ConnectionError as e:
            logger.exception(e)
            print(e.response.text, file=sys.stderr)


def create_pizzerias(file_path):
    create_pizzeria_flow()
    fill_pizzeria_addresses(file_path)


def create_pizzeria_flow():
    flow = {
        'name': 'Pizzeria',
        'description': 'Названия и адреса пиццерий'
    }
    field_names = ['name', 'description', 'type']
    field_descriptions = [
        ['Address', 'Адрес пиццерии', 'string'],
        ['Alias', 'Название пиццерии', 'string'],
        ['Longitude', 'Долгота', 'float'],
        ['Latitude', 'Широта', 'float']
    ]
    create_flow(flow, field_names, field_descriptions)


def create_customer_address_flow():
    flow = {
        'name': 'Customer_Address',
        'description': 'Адрес покупателя'
    }
    field_names = ['name', 'description', 'type']
    field_descriptions = [
        ['Customer_chat_id', 'chat_id покупателя', 'string'],
        ['Longitude', 'Долгота', 'float'],
        ['Latitude', 'Широта', 'float']
    ]
    create_flow(flow, field_names, field_descriptions)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    urllib3.disable_warnings()
    load_dotenv()

    online_shop.get_access_token(os.environ['STORE_CLIENT_ID'], os.environ['STORE_CLIENT_SECRET'])
    online_shop.set_headers()

    products_json_file_path = 'menu.json'
    pizzerias_addresses_json_file_path = 'addresses.json'

    create_products(products_json_file_path)

    create_pizzerias(pizzerias_addresses_json_file_path)

    create_customer_address_flow()


if __name__ == '__main__':
    main()
