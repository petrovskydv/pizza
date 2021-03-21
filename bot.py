import logging
import os
from textwrap import dedent

import telegram
from dotenv import load_dotenv
from more_itertools import chunked
from telegram import InlineKeyboardMarkup, LabeledPrice
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, PreCheckoutQueryHandler
from telegram.ext import Filters, Updater

import online_shop
from keyboards import get_products_keyboard, get_purchase_options_keyboard, get_cart_button, get_menu_button, \
    get_text_and_buttons_for_cart, get_pagination_buttons, get_delivery_buttons, get_payment_button
from utils import fetch_coordinates, get_nearest_pizzeria, get_delivery_cost_and_message_text, save_customer_address
from utils import get_database_connection

logger = logging.getLogger(__name__)


def start(update, context):
    """Хэндлер для состояния START.

    Выводит кнопки с товарами.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_MENU
    """
    page_number = context.chat_data.setdefault('page_number', 1)

    products = online_shop.get_all_products()
    product_pages = list(chunked(products, context.bot_data['products_per_page_number']))
    pages_count = len(product_pages)
    next_page_number = min(page_number + 1, pages_count)
    previous_page_number = max(1, page_number - 1)
    context.chat_data['current_page_number'] = page_number

    keyboard = get_products_keyboard(product_pages[page_number - 1])
    pagination_buttons = get_pagination_buttons(next_page_number, page_number, pages_count, previous_page_number)
    keyboard.append(pagination_buttons)
    keyboard.append([get_cart_button()])
    reply_markup = InlineKeyboardMarkup(keyboard)

    menu_text = 'Пожалуйста, выберите товар:'
    if update.message:
        update.message.reply_text(text=menu_text, reply_markup=reply_markup)
    elif update.callback_query:
        message = update.callback_query.message
        if len(message.photo) == 0:
            context.bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text=menu_text,
                                          reply_markup=reply_markup)
        else:
            context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            message.reply_text(text=menu_text, reply_markup=reply_markup)
    logger.info('Выведен список товаров')
    return 'HANDLE_MENU'


def handle_menu(update, context):
    """Хэндлер для состояния HANDLE_MENU.

    Выводит карточку товара из нажатой в меню кнопки, обрабатывает пагинацию, либо переходит в корзину или в меню.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: одно из состояний: HANDLE_MENU, HANDLE_CART_EDIT, HANDLE_DESCRIPTION
    """
    if update.message:
        return 'HANDLE_MENU'
    if update.callback_query:
        query = update.callback_query
        if query.data == 'cart':
            return handle_cart(update, context)
        elif query.data == 'back':
            return start(update, context)
        elif query.data == 'current':
            return 'HANDLE_MENU'

        if len(query.data) < 2:
            page_number = int(query.data)
            context.chat_data['page_number'] = page_number
            start(update, context)
            return 'HANDLE_MENU'

        logger.info(f'Выбран товар с id {query.data}')
        product = online_shop.get_product(query.data)

        keyboard = get_purchase_options_keyboard(product)
        keyboard.append([get_cart_button(), get_menu_button()])
        reply_markup = InlineKeyboardMarkup(keyboard)

        product_price = product['meta']['display_price']['with_tax']
        text = f"""\
        {product['name']}
        {product_price['formatted']}
        
        {product['description']}
        """
        try:
            image_id = product['relationships']['main_image']['data']['id']
            image_url = online_shop.get_file_href(image_id)
            context.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
            context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url, caption=dedent(text),
                                   reply_markup=reply_markup)
        except KeyError:
            context.bot.edit_message_text(text=dedent(text), chat_id=query.message.chat_id,
                                          message_id=query.message.message_id,
                                          reply_markup=reply_markup)
        logger.info(f'Выведен товар с id {query.data}')
        return 'HANDLE_DESCRIPTION'


def handle_description(update, context):
    """Хэндлер для состояния HANDLE_DESCRIPTION.

    Обрабатывает нажатие кнопок в карточке товара:
        * добавление товара в корзину
        * переход в меню
        * переход в корзину

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: одно из состояний: HANDLE_CART_EDIT, HANDLE_MENU, HANDLE_DESCRIPTION
    """
    if update.message:
        return 'HANDLE_DESCRIPTION'
    if update.callback_query:
        query = update.callback_query
        if query.data == 'cart':
            return handle_cart(update, context)
        elif query.data == 'back':
            return start(update, context)

        product_id, quantity = query.data.split(',')
        logger.info(f'Добавляем товар с id {product_id} в количестве {quantity} корзину {query.message.chat.id}')
        online_shop.add_product_to_cart(query.message.chat.id, product_id, int(quantity))
        query.answer('Товар добавлен в корзину')
        return 'HANDLE_DESCRIPTION'


def handle_cart(update, context):
    """Отображение корзины.

    Выводит состав корзины и сумму.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_CART_EDIT
    """
    query = update.callback_query
    logger.info(f'Выводим корзину {query.message.chat.id}')
    products = online_shop.get_cart_items(query.message.chat.id)

    keyboard, text = get_text_and_buttons_for_cart(products)
    keyboard.append([get_menu_button()])
    keyboard.append([get_payment_button()])
    reply_markup = InlineKeyboardMarkup(keyboard)

    cart = online_shop.get_cart(query.message.chat.id)
    total = cart['data']['meta']['display_price']['with_tax']['formatted']
    cart_text = f'''\
    {text}
        К оплате: {total}
    '''
    aligned_cart_text = dedent(cart_text)
    if len(query.message.photo) == 0:
        context.bot.edit_message_text(chat_id=query.message.chat.id, message_id=query.message.message_id,
                                      text=aligned_cart_text, reply_markup=reply_markup)
    else:
        context.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
        update.callback_query.message.reply_text(text=aligned_cart_text, reply_markup=reply_markup)

    context.chat_data['cart_text'] = aligned_cart_text

    return 'HANDLE_CART_EDIT'


def handle_cart_edit(update, context):
    """Хэндлер для состояния HANDLE_CART_EDIT.

    Обрабатывает нажатие кнопок в корзине.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: одно из состояний: HANDLE_MENU, HANDLE_LOCATION, HANDLE_CART_EDIT
    """
    if update.message:
        return 'HANDLE_CART_EDIT'
    if update.callback_query:
        query = update.callback_query
        if query.data == 'back':
            return start(update, context)
        elif query.data == 'payment':
            logger.info('Запрашиваем адрес покупателя')
            update.callback_query.message.reply_text(text='Пришлите, пожалуйста, ваш адрес текстом или геолокацию')
            return 'HANDLE_LOCATION'

        logger.info(f'Удаляем из корзины {query.message.chat.id} товар с id {query.data}')
        online_shop.remove_product_from_cart(query.message.chat.id, query.data)
        handle_cart(update, context)
        return 'HANDLE_CART_EDIT'


def handle_location(update, context):
    """Хэндлер для состояния HANDLE_LOCATION.

    Обрабатывает полученные координаты или адрес и записывает в CRM, предлагает варианты: доставка или самовывоз.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_NEW_ORDER
    """
    if update.message:
        message = update.message
        if message.location:
            current_position = (message.location.latitude, message.location.longitude)
            logger.info(f'Получили геолокацию с координатами {current_position}')
        else:
            logger.info(f'Получили текст адреса {message.text}')
            current_position = fetch_coordinates(context.bot_data['yandex_geocoder_token'], message.text)
            if current_position:
                logger.info(f'Получили координаты {current_position}')
            else:
                logger.info('Не удалось получить координаты')
                message.reply_text(text='Не удалось распознать адрес. Попробуйте ввести еще раз')
                return 'HANDLE_LOCATION'

        pizzerias = online_shop.get_all_entries(context.bot_data['pizzerias_flow_name'])
        nearest_pizzeria = get_nearest_pizzeria(current_position, pizzerias)
        delivery_cost, message_text = get_delivery_cost_and_message_text(nearest_pizzeria)

        keyboard = get_delivery_buttons()
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(text=dedent(message_text), reply_markup=reply_markup)

        address_id = save_customer_address(message.chat_id, current_position)

        context.chat_data['nearest_pizzeria'] = nearest_pizzeria
        context.chat_data['address_id'] = address_id
        context.chat_data['delivery_cost'] = delivery_cost

    return 'HANDLE_NEW_ORDER'


def handle_new_order(update, context):
    """Хэндлер для состояния HANDLE_NEW_ORDER.

    Обрабатывает выбранный вариант доставки:
        * при самовывозе заканчивает диалог
        * при доставке отправляет сообщение доставщику о заказе и предлагает покупателю оплатить заказ

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_WAITING_PAYMENT, HANDLE_NEW_ORDER или HANDLE_FINISH
    """
    if update.message:
        return 'HANDLE_NEW_ORDER'
    if update.callback_query:
        query = update.callback_query
        nearest_pizzeria = context.chat_data['nearest_pizzeria']
        if query.data == 'delivery':
            customer_address = online_shop.get_entry('Customer_Address', context.chat_data['address_id'])
            deliver_telegram_id = nearest_pizzeria['pizzeria']['Deliver_telegram_id']

            query.bot.send_message(chat_id=deliver_telegram_id, text=context.chat_data['cart_text'])
            delivery_cost = context.chat_data.setdefault('delivery_cost', 0)
            if delivery_cost > 0:
                query.bot.send_message(chat_id=deliver_telegram_id, text=f'Стоимость доставки {delivery_cost}')
            query.bot.send_location(chat_id=deliver_telegram_id, latitude=customer_address['Latitude'],
                                    longitude=customer_address['Longitude'])

            context.job_queue.run_once(get_feedback, 30, context=query.message.chat_id)

            keyboard = [[get_payment_button()]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(text='Для оплаты нажмите кнопку "Оплатить"', reply_markup=reply_markup)

            return 'HANDLE_WAITING_PAYMENT'

        elif query.data == 'pick-up':
            query.message.reply_text(text=f'Адрес ближайшей пиццерии {nearest_pizzeria["pizzeria"]["Address"]}')

    return 'HANDLE_FINISH'


def start_payment(update, context):
    if update.message:
        return 'HANDLE_WAITING_PAYMENT'
    if update.callback_query:
        query = update.callback_query
        logger.info(f'Начинаем оплату корзины {query.message.chat.id}')
        chat_id = query.message.chat_id
        title = 'Оплата заказа'
        description = 'Пицца'
        payload = context.bot_data['payload_name']
        provider_token = context.bot_data['bank_token']
        start_parameter = 'test-payment'
        currency = context.bot_data['currency']
        prices = []
        products = online_shop.get_cart_items(query.message.chat.id)
        for product in products:
            product_price = product['meta']['display_price']['with_tax']
            prices.append(LabeledPrice(product['name'], product_price['value']['amount']))
        delivery_cost = context.chat_data.setdefault('delivery_cost', 0)

        if delivery_cost > 0:
            # price * 100 so as to include 2 decimal points
            prices.append(LabeledPrice('Доставка', delivery_cost * 100))

        context.bot.send_invoice(chat_id, title, description, payload, provider_token, start_parameter, currency,
                                 prices)
        return 'HANDLE_FINISH'


def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != context.bot_data['payload_name']:
        query.answer(ok=False, error_message='Something went wrong...')
    else:
        query.answer(ok=True)
        logger.info(f'Начало платы от пользователя {query["from_user"]["id"]} на сумму {query["total_amount"]}')


def successful_payment_callback(update, context):
    payment = update.message.successful_payment
    update.message.reply_text('Спасибо за покупку!')
    logger.info(
        f'Оплата от пользователя {update.message["from_user"]["id"]} на сумму {payment["total_amount"]} прошла успешно')


def handle_finish(update, context):
    message_text = 'Оформление заказа окончено. Чтобы начать новый заказ введите /start'
    if update.message:
        message = update.message
        message.reply_text(text=message_text)
    elif update.callback_query:
        message = update.callback_query.message
        message.reply_text(text=message_text)
    return 'HANDLE_FINISH'


def get_feedback(context):
    message_text = '''\
    Приятного аппетита! *место для рекламы*

    *сообщение что делать если пицца не пришла*
    '''
    context.bot.send_message(chat_id=context.job.context, text=dedent(message_text))


def handle_users_reply(update, context):
    """Хэндлер для обработки всех сообщений.

    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        None
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    chat_id_key = f'telegramid_{chat_id}'

    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id_key).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART_EDIT': handle_cart_edit,
        'HANDLE_LOCATION': handle_location,
        'HANDLE_NEW_ORDER': handle_new_order,
        'HANDLE_WAITING_PAYMENT': start_payment,
        'HANDLE_FINISH': handle_finish
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    db.set(chat_id_key, next_state)


def handle_error(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    load_dotenv()

    online_shop.get_access_token()
    online_shop.set_headers()

    updater = Updater(os.environ['TELEGRAM_TOKEN'])
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.location, handle_users_reply))
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment_callback))
    dispatcher.add_error_handler(handle_error)

    products_per_page_number = 7
    dispatcher.bot_data['products_per_page_number'] = products_per_page_number
    dispatcher.bot_data['yandex_geocoder_token'] = os.environ['YANDEX_GEOCODER_TOKEN']
    dispatcher.bot_data['bank_token'] = os.environ['BANK_TOKEN']
    dispatcher.bot_data['pizzerias_flow_name'] = 'Pizzeria'
    dispatcher.bot_data['currency'] = 'RUB'
    dispatcher.bot_data['payload_name'] = 'Custom-Payload'

    updater.start_polling()
