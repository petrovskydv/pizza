from telegram import InlineKeyboardButton


def get_products_keyboard(products):
    keyboard = []
    for product in products:
        keyboard.append(
            [
                InlineKeyboardButton(product['name'], callback_data=product['id'])
            ]
        )
    return keyboard


def get_purchase_options_keyboard(product):
    purchase_options = (1, 2, 3)

    keyboard = []
    purchase_option_button = []
    for purchase_option in purchase_options:
        purchase_option_button.append(
            InlineKeyboardButton(f'{purchase_option} шт.', callback_data=f'{product["id"]},{purchase_option}')
        )
    keyboard.append(purchase_option_button)
    return keyboard


def get_cart_button():
    return InlineKeyboardButton('Корзина', callback_data='cart')


def get_menu_button():
    return InlineKeyboardButton('В меню', callback_data='back')


def get_text_and_buttons_for_cart(products):
    cart_text = ' '
    keyboard = []
    for product in products:
        product_price = product['meta']['display_price']['with_tax']

        cart_text = f"""
        {cart_text}
        {product['name']}
        {product['description']}
        {product_price['unit']['formatted']}
        {product["quantity"]} шт. на сумму {product_price["value"]["formatted"]}
        """

        keyboard.append([InlineKeyboardButton(f'Убрать из корзины {product["name"]}',
                                              callback_data=product['id'])])
    return keyboard, cart_text


def get_pagination_buttons(next_page_number, page_number, pages_count, previous_page_number):
    pagination_buttons = []
    if page_number > 1:
        pagination_buttons.append(
            InlineKeyboardButton(f'Предыдущая', callback_data=str(previous_page_number))
        )
    pagination_buttons.append(InlineKeyboardButton(f'Страница {page_number} из {pages_count}', callback_data='current'))
    if page_number != pages_count:
        pagination_buttons.append(
            InlineKeyboardButton(f'Следующая', callback_data=str(next_page_number))
        )
    return pagination_buttons
