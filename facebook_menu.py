import os


def get_categories_card(categories, front_page_category_id):
    categories_image_url = os.environ['CATEGORIES_IMAGE_URL']
    category_buttons = []
    for category in categories:
        if category['id'] == front_page_category_id:
            continue
        category_buttons.append({
            'type': 'postback',
            'title': category['name'],
            'payload': f'category_{category["id"]}'
        })

    categories_card = {
        'title': 'Не нашли нужную пиццу?',
        'subtitle': 'Остальные пиццы можно посмотреть в одной и категорий',
        'image_url': categories_image_url,
        'buttons': category_buttons
    }
    return categories_card


def get_product_card(product, product_image_url):
    return {
        'title': f'{product["name"]} ({product["price"]})',
        'subtitle': product['description'],
        'image_url': product_image_url,
        'buttons': [
            {
                'type': 'postback',
                'title': 'добавить в корзину',
                'payload': f'product_{product["id"]}'
            }
        ]
    }


def get_menu_card():
    pizzeria_logo_url = os.environ['PIZZERIA_LOGO_URL']
    return {
        'title': 'Меню',
        'subtitle': 'Здесь вы можете выбрать один из вариантов',
        'image_url': pizzeria_logo_url,
        'buttons': [
            {
                'type': 'postback',
                'title': 'Корзина',
                'payload': 'cart'
            },
            {
                'type': 'postback',
                'title': 'Акции',
                'payload': 'promotions'
            },
            {
                'type': 'postback',
                'title': 'Сделать заказ',
                'payload': 'make_order'
            },
        ]
    }


def get_cart_product_card(product):
    product_price = product['meta']['display_price']['with_tax']
    return {
        'title': f'{product["name"]} - {product["quantity"]} шт.'
                 f' на сумму {product_price["value"]["formatted"]}',
        'subtitle': product['description'],
        'image_url': product['image']['href'],
        'buttons': [
            {
                'type': 'postback',
                'title': 'Добавить еще одну',
                'payload': f'product_{product["product_id"]}'
            },
            {
                'type': 'postback',
                'title': 'Убрать из корзины',
                'payload': f'delete_product_{product["id"]}'
            }
        ]
    }


def get_cart_card(cart):
    cart_logo_url = os.environ['CART_LOGO_URL']
    return {
        'title': f"Ваш заказ на сумму {cart['data']['meta']['display_price']['with_tax']['formatted']}",
        'subtitle': 'Здесь вы можете выбрать один из вариантов',
        'image_url': cart_logo_url,
        'buttons': [
            {
                'type': 'postback',
                'title': 'Самовывоз',
                'payload': 'pick-up'
            },
            {
                'type': 'postback',
                'title': 'Доставка',
                'payload': 'delivery'
            },
            {
                'type': 'postback',
                'title': 'К меню',
                'payload': '/start'
            },
        ]
    }


def get_generic_template_message(elements):
    message = {
        'attachment': {
            'type': 'template',
            'payload': {
                'template_type': 'generic',
                'image_aspect_ratio': 'square',
                'elements': elements
            }
        }
    }
    return message
