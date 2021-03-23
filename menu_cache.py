import json
import logging

import online_shop
from utils import get_database_connection

logger = logging.getLogger(__name__)


def save_products():
    db = get_database_connection()
    all_products = online_shop.get_all_products()
    for product in all_products:
        image_url = online_shop.get_file_href(product['image_id'])
        logger.info(f'Сохраняем ссылку на изображение товара {product["name"]} в кеш')
        db.set(
            product['id'],
            json.dumps(
                {
                    'image_url': image_url,
                    'product': product
                }
            )
        )


def save_categories():
    db = get_database_connection()
    categories = online_shop.get_all_categories()
    logger.info('Сохраняем список категорий в кеш')
    db.set('categories', json.dumps(categories))
    for category in categories:
        products = online_shop.get_products_by_category_id(category['id'])
        logger.info(f'Сохраняем товары категории {category["name"]} в кеш')
        db.set(category['id'], json.dumps(products))


def main():
    save_products()
    save_categories()


if __name__ == '__main__':
    main()
