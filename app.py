import json
import logging
import os

import requests
from dotenv import load_dotenv
from flask import Flask, request

import online_shop
from utils import get_database_connection

app = Flask(__name__)

logger = logging.getLogger(__name__)


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
                if messaging_event.get('message'):
                    sender_id = messaging_event['sender']['id']
                    recipient_id = messaging_event['recipient']['id']
                    message_text = messaging_event['message']['text']
                    send_message(sender_id, message_text)
                    handle_users_reply(sender_id, message_text)
    return 'ok', 200


def handle_users_reply(sender_id, message_text):
    db = get_database_connection()
    states_functions = {
        'START': handle_start,
    }
    chat_id_key = f'facebookid_{sender_id}'
    recorded_state = db.get(chat_id_key)
    if not recorded_state or recorded_state.decode("utf-8") not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state.decode("utf-8")

    if message_text == "/start":
        user_state = "START"

    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    db.set(chat_id_key, next_state)


def send_message(recipient_id, message_text):
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}
    request_content = json.dumps({
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': message_text
        }
    })
    response = requests.post('https://graph.facebook.com/v2.6/me/messages', params=params, headers=headers,
                             data=request_content)
    response.raise_for_status()


def handle_start(sender_id, message_text):
    params = {'access_token': os.environ['PAGE_ACCESS_TOKEN']}
    headers = {'Content-Type': 'application/json'}

    front_page_category_id = '40874a97-fdb2-452b-81a3-0dfb2dfeee1a'
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
                        'payload': product['id']
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
                'payload': category['id']
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

    request_content = json.dumps({
        'recipient': {
            'id': sender_id
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'image_aspect_ratio': 'square',
                    'elements': elements
                }
            }
        }
    })
    response = requests.post('https://graph.facebook.com/v2.6/me/messages', params=params, headers=headers,
                             data=request_content)
    response.raise_for_status()

    return "START"


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    load_dotenv()
    online_shop.get_access_token()
    online_shop.set_headers()
    app.run(debug=True)
