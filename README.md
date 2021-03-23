# Магазин в [Telegram](https://t.me/denpet_bot) и [Facebook](https://www.facebook.com/)

Прямо в [Telegram](https://t.me/denpet_bot) можно оформить и оплатить заказ в онлайн-магазине.
Магазин работает на платформе [Elastic Path](https://www.elasticpath.com/).

При заказе клиент отправляет свой адрес или геолокацию, бот определяет ближайшую торговую точку.
Если клиент выбрал доставку, а не самовывоз, клиент может оплатить заказ, а курьеру отправляется сигнал – какую пиццу и куда везти.

А так же заказ можно оформить в [Facebook](https://www.facebook.com/)

## Создание бота в [Telegram](https://telegram.org/)
Вы получите его API ключ. Выглядит он так:
```
95132391:wP3db3301vnrob33BZdb33KwP3db3F1I
```
Для этого нужно:
1. Написать [Отцу ботов](https://telegram.me/BotFather)
    * `/start`
    * `/newbot`

Отец ботов попросит ввести два имени. Первое — как он будет отображаться в списке контактов, можно написать на русском. Второе — имя, по которому бота можно будет найти в поиске. Должно быть английском и заканчиваться на bot (например, `notification_bot`)


## Создание страницы в [Facebook](https://www.facebook.com/)
[Здесь](https://gist.github.com/voron434/3765d14574067d17aa9e676145df360e) есть пошаговый туториал.

## Как установить
Скачайте проект на свой компьютер.
В папке проекта необходимо создать файл `.env`. В этом файле нужно создать переменные, указанные в образце.

Образец файла:
```
TELEGRAM_TOKEN='<API-ключ бота>'
REDIS_HOST='адрес хоста базы данных Redis'
REDIS_PORT=<порт хоста базы данных Redis>
REDIS_PASSWORD='<пароль хоста базы данных Redis>'
STORE_CLIENT_ID='API-ключ интернет магазина'
STORE_CLIENT_SECRET='пароль интернет магазина'
YANDEX_GEOCODER_TOKEN='токен яндекс-геокодер'
BANK_TOKEN='токен платежной системы'
PAGE_ACCESS_TOKEN='токен для facebook'
VERIFY_TOKEN='маркер подтверждения webhook'
FRONT_PAGE_CATEGORY_ID='id начальной категории'
PIZZERIA_LOGO_URL='url лого пиццерии'
CATEGORIES_IMAGE_URL='url картинки категорий'
CART_LOGO_URL='url картинки корзины'
```

Аккаунт на платформе [Elastic Path](https://www.elasticpath.com/) должен быть уже заведен. `STORE_CLIENT_ID` и `STORE_CLIENT_SECRET` можно найти на главной странице личного кабинета.

Tокен яндекс-геокодер нужно получить в [кабинете разработчика](https://developer.tech.yandex.ru/).

В Telegram уже есть интеграция с несколькими популярными банками. Для получения токена понадобится:
* Меню Payments у BotFather
  - /mybots, выберите бота, Payments
* Выбрать банк и получить токен.

Вы получите сообщение следующего вида:
```
Payment providers for Devman Test @dvmn_test_bot.

1 method connected:
- Bank title: 971399174:TEST:rbvor23-ofbu2-2b49-923bf3bf2b3uf 2015-01-01 14:07
```

Python3 должен быть уже установлен. Затем используйте pip (или pip3, если есть конфликт с Python2) для установки зависимостей:
```
pip install -r requirements.txt
```


## Как запустить

Перед запуском бота необходимо загрузить данные о товарах и торговых точках.
Данные о товарах содержаться в файле `menu.json` в папке проекта.

Образец файла:
```json
[
  {
    "id": 20,
    "name": "Чизбургер-пицца",
    "description": "мясной соус болоньезе, моцарелла, лук, соленые огурчики, томаты, соус бургер",
    "food_value": {
      "fats": "6,9",
      "proteins": "7,5",
      "carbohydrates": "23,72",
      "kiloCalories": "188,6",
      "weight": "470±50"
    },
    "culture_name": "ru-RU",
    "product_image": {
      "url": "https://dodopizza-a.akamaihd.net/static/Img/Products/Pizza/ru-RU/1626f452-b56a-46a7-ba6e-c2c2c9707466.jpg",
      "height": 1875,
      "width": 1875
    },
    "price": 395
  },
  {
    "id": 122,
    "name": "Крэйзи пепперони ",
    "description": "Томатный соус, увеличенные порции цыпленка и пепперони, моцарелла, кисло-сладкий соус",
    "food_value": {
      "fats": "7,64",
      "proteins": "9,08",
      "carbohydrates": "31,33",
      "kiloCalories": "232,37",
      "weight": "410±50"
    },
    "culture_name": "ru-RU",
    "product_image": {
      "url": "https://dodopizza-a.akamaihd.net/static/Img/Products/Pizza/ru-RU/7aa1638e-1bee-4162-a2df-6bbaf683a486.jpg",
      "height": 1875,
      "width": 1875
    },
    "price": 395
  }
]
```
Данные о торговых точках содержпться в файле `addresses.json` в папке проекта.
Образец файла:
```json
[
  {
    "id": "00000351-0000-0000-0000-000000000000",
    "alias": "Афимолл",
    "address": {
      "full": "Москва, набережная Пресненская дом 2",
      "city": "Москва",
      "street": "Пресненская",
      "street_type": "набережная",
      "building": "2"
    },
    "coordinates": {
      "lat": "55.749299",
      "lon": "37.539644"
    }
  },
  {
    "id": "0000020e-0000-0000-0000-000000000000",
    "alias": "Ясенево",
    "address": {
      "full": "Москва, проспект Новоясеневский дом вл7",
      "city": "Москва",
      "street": "Новоясеневский",
      "street_type": "проспект",
      "building": "вл7"
    },
    "coordinates": {
      "lat": "55.607489",
      "lon": "37.532367"
    }
  }
]
```
Для загрузки данных необходимо ввести в командной строке:
```
python shop_data.py
```
Далее необходимо обновить кэш бота:
```
python menu_cache.py
```
Кэш будет обновляться автоматически при изменении категории или товара. Для этого надо настроить раздел `Integrations` в настройках онлайн-магазина [Elastic Path](https://www.elasticpath.com/).


Для запуска бота [Telegram](https://telegram.org/) на компьютере необходимо ввести в командной строке:
```
python bot.py
```
Для запуска бота [Facebook](https://www.facebook.com/) на компьютере необходимо ввести в командной строке:
```
python app.py
```

## Цель проекта
Код написан в образовательных целях на онлайн-курсе для веб-разработчиков [dvmn.org](https://dvmn.org/).

## Лицензия

Этот проект находится под лицензией MIT License - подробности см. в файле LICENSE.