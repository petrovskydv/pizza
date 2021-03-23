import json
import logging
import os
from traceback import print_exc

import requests
from dotenv import load_dotenv
from flask import Flask, request

import online_shop
from facebook_menu import get_categories_card, get_product_card, get_menu_card, get_cart_product_card, get_cart_card, \
    get_generic_template_message
from utils import get_database_connection, get_facebook_cart_id

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
                else:
                    return
                logger.info(f'Обрабатываем сообщение {message_text}')
                handle_users_reply(sender_id, message_text)
    return 'ok', 200


def handle_users_reply(sender_id, message_text):
    db = get_database_connection()

    states_functions = {
        'START': handle_start,
        'MENU': handle_menu,
    }

    chat_id_key = get_facebook_cart_id(sender_id)
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
    cart_id = get_facebook_cart_id(sender_id)
    if message_text.startswith('category_'):
        return handle_start(sender_id, message_text)

    if message_text.startswith('product_'):
        db = get_database_connection()
        product_id = message_text.replace('product_', '')
        logger.info(f'Добавляем товар с id {product_id} в корзину {cart_id}')
        online_shop.add_product_to_cart(cart_id, product_id, quantity=1)
        # TODO взять данные из кеша
        # product = online_shop.get_product(product_id)
        product = json.loads(db.get(product_id))['product']
        send_message(sender_id, {'text': f'В корзину добавлена пицца {product["name"]}'})
        show_cart(sender_id, 'cart')

    if message_text.startswith('delete_product_'):
        product_id = message_text.replace('delete_product_', '')
        logger.info(f'Удаляем товар с id {product_id} из корзины {cart_id}')
        online_shop.remove_product_from_cart(cart_id, product_id)
        send_message(sender_id, {'text': 'Пицца удалена из корзины'})
        show_cart(sender_id, 'cart')

    if message_text == 'cart':
        show_cart(sender_id, message_text)

    return 'MENU'


def send_message(recipient_id, message):
    logger.info(f'Отправляем сообщение в чат адресату с id {recipient_id}')
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
        # TODO добавить обработку остальных исключений и перенести их в handle_users_reply
        #  чтобы ловить исключения при обращении к магазину
        print_exc()
        logger.error(e.response.text)


def handle_start(sender_id, message_text):
    if message_text == '/start':
        # TODO начальную категорию вынести в переменные
        # front_page_category_id = '40874a97-fdb2-452b-81a3-0dfb2dfeee1a'
        front_page_category_id = os.environ['FRONT_PAGE_CATEGORY_ID']
    elif message_text.startswith('category_'):
        front_page_category_id = message_text.replace('category_', '')
    else:
        return 'START'
    db = get_database_connection()

    logger.info(f'Читаем из кеша товары категории с id {front_page_category_id}')
    category_products = json.loads(db.get(front_page_category_id))
    # TODO лого пиццерии в переменные
    # pizzeria_logo_url = 'https://image.freepik.com/free-vector/pizza-logo-design-template_15146-192.jpg'
    pizzeria_logo_url = os.environ['PIZZERIA_LOGO_URL']
    elements = [get_menu_card(pizzeria_logo_url)]

    for product in category_products:
        logger.info(f'Читаем из кеша ссылку на картинку для товара с id {product["id"]}')
        product_image_url = json.loads(db.get(product['id']))['image_url']
        elements.append(
            get_product_card(product, product_image_url)
        )

    logger.info('Читаем категории из кеша')
    categories = json.loads(db.get('categories'))
    # TODO картинку категорий вынести в переменные
    # categories_image_url = 'https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg'
    categories_image_url = os.environ['CATEGORIES_IMAGE_URL']
    elements.append(
        get_categories_card(categories_image_url, categories, front_page_category_id)
    )

    message = get_generic_template_message(elements)
    send_message(sender_id, message)

    return 'MENU'


def show_cart(sender_id, message_text):
    if message_text != 'cart':
        return 'MENU'

    cart_id = get_facebook_cart_id(sender_id)
    cart = online_shop.get_cart(cart_id)
    cart_products = online_shop.get_cart_items(cart_id)
    # TODO картинку корзины вынести в переменные
    # cart_logo_url = 'https://postium.ru/wp-content/uploads/2018/08/idealnaya-korzina-internet-magazina-1068x713.jpg'
    cart_logo_url = os.environ['CART_LOGO_URL']
    elements = [get_cart_card(cart, cart_logo_url)]

    for product in cart_products:
        elements.append(
            get_cart_product_card(product)
        )

    message = get_generic_template_message(elements)
    send_message(sender_id, message)

    return 'MENU'


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger.info('Запуск')
    load_dotenv()
    online_shop.get_access_token()
    online_shop.set_headers()
    app.run(debug=True)


if __name__ == '__main__':
    main()
