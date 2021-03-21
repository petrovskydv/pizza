import json
import logging
import os
from pprint import pprint
from traceback import print_exc

import requests
from dotenv import load_dotenv
from flask import Flask, request

import online_shop
from utils import get_database_connection

logger = logging.getLogger('facebook_bot')
app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == os.environ['VERIFY_TOKEN']:
            return 'Verification token mismatch', 403
        return request.args['hub.challenge'], 200

    return 'Hello world', 200


@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                sender_id = messaging_event['sender']['id']
                if messaging_event.get('message'):
                    message_text = messaging_event['message']['text']
                elif messaging_event.get('postback'):
                    message_text = messaging_event['postback']['payload']
                logger.info(f'Обрабатываем сообщение {message_text}')
                handle_users_reply(sender_id, message_text)
    return 'ok', 200


def handle_users_reply(sender_id, message_text):
    db = get_database_connection()
    states_functions = {
        'START': handle_start,
        'MENU': handle_menu,
    }
    chat_id_key = get_cart_id(sender_id)
    recorded_state = db.get(chat_id_key)
    logger.info(f'Прочитали текущее состояние из БД: {recorded_state}')
    if not recorded_state or recorded_state.decode('utf-8') not in states_functions.keys():
        user_state = 'START'
    else:
        user_state = recorded_state.decode('utf-8')

    if message_text == '/start':
        user_state = 'START'

    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    db.set(chat_id_key, next_state)
    logger.info(f'Записали состояние в БД: {next_state}')


def handle_menu(sender_id, message_text):
    if message_text.startswith('category_'):
        return handle_start(sender_id, message_text)

    if message_text.startswith('product_'):
        product_id = message_text.replace('product_', '')
        cart_id = get_cart_id(sender_id)
        logger.info(
            f'Добавляем товар с id {product_id} в корзину {cart_id}')
        online_shop.add_product_to_cart(cart_id, product_id, quantity=1)
        product = online_shop.get_product(product_id)
        send_message(sender_id, {'text': f'В корзину добавлена пицца {product["name"]}'})
        show_cart(sender_id, 'cart')

    if message_text.startswith('delete_product_'):
        product_id = message_text.replace('delete_product_', '')
        cart_id = get_cart_id(sender_id)
        logger.info(
            f'Удаляем товар с id {product_id} из корзины {cart_id}')
        online_shop.remove_product_from_cart(cart_id, product_id)
        send_message(sender_id, {'text': 'Пицца удалена из корзины'})
        show_cart(sender_id, 'cart')

    if message_text == 'cart':
        show_cart(sender_id, message_text)

    return 'MENU'


def get_cart_id(sender_id):
    return f'facebookid_{sender_id}'


def send_message(recipient_id, message):
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    request_content = json.dumps({
        'recipient': {
            'id': recipient_id
        },
        'message': message
    })
    try:
        response = requests.post('https://graph.facebook.com/v2.6/me/messages', params=params, headers=headers,
                                 data=request_content)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print_exc()
        logger.info(e.response.text)


def handle_start(sender_id, message_text):
    if message_text == '/start':
        front_page_category_id = '40874a97-fdb2-452b-81a3-0dfb2dfeee1a'
    elif message_text.startswith('category_'):
        front_page_category_id = message_text.replace('category_', '')
    else:
        return 'START'

    products = online_shop.get_products_by_category_id(front_page_category_id)
    logo_url = 'https://image.freepik.com/free-vector/pizza-logo-design-template_15146-192.jpg'
    elements = [
        {
            'title': 'Меню',
            'subtitle': 'Здесь вы можете выбрать один из вариантов',
            'image_url': logo_url,
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
    ]

    for product in products:
        image_url = online_shop.get_file_href(product['image_id'])
        elements.append(
            {
                'title': f'{product["name"]} ({product["price"]})',
                'subtitle': product['description'],
                'image_url': image_url,
                'buttons': [
                    {
                        'type': 'postback',
                        'title': 'добавить в корзину',
                        'payload': f'product_{product["id"]}'
                    }
                ]
            }
        )

    category_buttons = []
    categories = online_shop.get_all_categories()
    for category in categories:
        if category['id'] == front_page_category_id:
            continue
        category_buttons.append(
            {
                'type': 'postback',
                'title': category['name'],
                'payload': f'category_{category["id"]}'
            }
        )

    categories_image_url = 'https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg'
    elements.append(
        {
            'title': 'Не нашли нужную пиццу?',
            'subtitle': 'Остальные пиццы можно посмотреть в одной и категорий',
            'image_url': categories_image_url,
            'buttons': category_buttons
        }
    )

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
    send_message(sender_id, message)

    return 'MENU'


def show_cart(sender_id, message_text):
    if message_text != 'cart':
        return 'MENU'

    cart_id = get_cart_id(sender_id)
    cart = online_shop.get_cart(cart_id)
    cart_products = online_shop.get_cart_items(cart_id)
    cart_logo_url = 'https://postium.ru/wp-content/uploads/2018/08/idealnaya-korzina-internet-magazina-1068x713.jpg'
    elements = [
        {
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
    ]

    for product in cart_products:
        product_price = product['meta']['display_price']['with_tax']
        elements.append(
            {
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
        )
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
    send_message(sender_id, message)

    return 'CART'


def send_request(headers, params, request_content):
    response = requests.post('https://graph.facebook.com/v2.6/me/messages', params=params, headers=headers,
                             data=request_content)
    response.raise_for_status()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger.info('Запуск')
    load_dotenv()
    online_shop.get_access_token()
    online_shop.set_headers()
    app.run(debug=True)
