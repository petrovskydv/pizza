import logging

import requests
from geopy import distance

logger = logging.getLogger(__name__)


def fetch_coordinates(apikey, place):
    logger.info(f'Получаем координаты {place} через геокодер')
    base_url = "https://geocode-maps.yandex.ru/1.x"
    params = {"geocode": place, "apikey": apikey, "format": "json"}
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']
    if len(found_places) == 0:
        return
    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lat, lon


def get_nearest_pizzeria(current_position, pizzerias):
    pizzerias_distances = []
    for pizzeria in pizzerias:
        pizzeria_distance = distance.distance(
            (pizzeria['Latitude'], pizzeria['Longitude']),
            current_position
        ).m
        pizzerias_distances.append(
            {
                'pizzeria': pizzeria,
                'distance': int(pizzeria_distance)
            }
        )
    nearest_pizzeria = min(pizzerias_distances, key=lambda x: x['distance'])
    logger.info(f'Нашли ближайшую пиццерию{nearest_pizzeria}')
    return nearest_pizzeria


def get_delivery_cost_and_message_text(nearest_pizzeria):
    nearest_pizzeria_distance = nearest_pizzeria['distance']
    nearest_pizzeria_distance_km = round(nearest_pizzeria_distance / 1000, 1)
    nearest_pizzeria_address = nearest_pizzeria['pizzeria']['Address']

    message_text_template = '''\
        Можете забрать пиццу из нашей пиццерии бесплатно или заказать доставку. 
        Ближайшая пиццерия находится в {}км от вас! 
        Вот ее адрес: {} 
        
        Стоимость доставки: {} рублей.'''

    delivery_cost = 0
    if nearest_pizzeria_distance < 500:
        message_text = f'''\
        Может заберете пиццу из нашей пиццерии неподалеку? 
        Она всего в {nearest_pizzeria_distance} м от вас! 
        Вот ее адрес: {nearest_pizzeria_address}.

        А можем и бесплатно доставить.'''
    elif nearest_pizzeria_distance > 20000:
        message_text = f'''\
        Так далеко доставить пиццу не сможем. Доступен только самовывоз!
        Ближайшая пиццерия находится в {round(nearest_pizzeria_distance / 1000, 1)} км от вас!
        Вот ее адрес: {nearest_pizzeria_address}.'''
    elif nearest_pizzeria_distance < 5000:
        delivery_cost = 100
        message_text = message_text_template.format(nearest_pizzeria_distance_km,
                                                    nearest_pizzeria_address, delivery_cost)
    elif nearest_pizzeria_distance < 20000:
        delivery_cost = 300
        message_text = message_text_template.format(nearest_pizzeria_distance_km,
                                                    nearest_pizzeria_address, delivery_cost)
    return delivery_cost, message_text
