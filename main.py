import json
import logging
import os

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


def create_products():
    products = open_json_file('menu.json')
    for product in products:
        try:
            product_id = online_shop.create_product(product)
            image_file = download_image(f"{product['name']}.jpg", product['product_image']['url'])
            image_id = online_shop.create_file(image_file)
            online_shop.create_product_main_image(product_id, image_id)
        except requests.exceptions.HTTPError as e:
            print(e.response.text)


def create_flow():
    flow_id = online_shop.create_flow('Pizzeria', 'Названия и адреса пиццерий')



def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    urllib3.disable_warnings()
    load_dotenv()
    online_shop.get_access_token(os.environ['STORE_CLIENT_ID'], os.environ['STORE_CLIENT_SECRET'])
    online_shop.set_headers()

    # create_products()


if __name__ == '__main__':
    main()
