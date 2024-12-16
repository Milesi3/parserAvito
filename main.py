# -*- coding: utf-8 -*-
""" Скрипт отправки метрик по количеству квартир, средней и медианной цены на сегодня """
# meta_top_resource_role: service
# meta_top_resource_category: cloud
# meta_tenant: *
# meta_env: *
# meta_stage: *
# meta_doc:
# meta_owner: https://online.sbis.ru/person/0b465217-b227-44e7-bd21-167ebd34af0e
# meta_short_description: Скрипт отправки метрик по состоянию сервисов


import time
import statistics
from expmonitoring import Monitoring
from selenium import webdriver
from selenium_stealth import stealth
from bs4 import BeautifulSoup


def init_webdriver():
    """ Инициализация драйвера Chrome """
    driver = webdriver.Chrome()
    # Фейк параметры о себе
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine"
            )
    return driver


def get_product_info(driver, url):
    """ Сбор информации со страницы """
    # Открытие страницы и форматирование в фромате lxml
    driver.get(url)
    main_page_html = BeautifulSoup(driver.page_source, "lxml")
    # Нахождение карточек квартир
    content = main_page_html.find("div", {"data-marker": "catalog-serp"})
    cards = content.findChildren(recursive=False)
    # Формирования списка ключ-значение с квартирами с нужной информацией
    all_cards = []
    number_cards = 0
    for card in cards:
        card_name = card.find("a", title=True)["title"]
        card_url = card.find("a", href=True)["href"]
        product_url = "https://www.avito.ru" + card_url
        # Нахождение веремени создания карточки
        time_card = get_time_info(driver, product_url)
        # Ограничение: нахождения только нужного временного отрезка
        if "вчера" not in time_card:
            return all_cards
        # Время 16-12-24 20:00
        time_card = f'{time.strftime("%Y-%m-%d")} {str(time_card.split(" ")[2])}'
        # Отсеивание лишних баннеров
        try:
            price = card.find("p", {"data-marker": "item-price"})
            price = price.findChildren(recursive=False)[1]["content"]  # Цена
            card_info = {number_cards: {"name": card_name,
                                        "url": product_url,
                                        "price": price,
                                        "time": time_card
                                        }
                         }
            all_cards.append(card_info)
            number_cards += 1
        except TypeError:
            print('Вонючий баннер был отсеян')
    return all_cards


def get_time_info(driver, product_url):
    """ Нахождение веремени создания карточки """
    # Открытие страницы и форматирование в фромате lxml
    driver.get(product_url)
    card_page_html = BeautifulSoup(driver.page_source, "lxml")
    # Нахождение времени
    time_card = (card_page_html.find("span", {"data-marker": "item-view/item-date"})
                 .text.replace(" · ", ""))
    return time_card


def get_statistic_info(all_cards):
    """ Нахождение статистики
         1. Средняя стоимость
         2. Медианная цена
         3. timestamp
         4. Колличество карточек
     """
    prices = []
    card_counter = 0
    # Нахождение цен в словаре
    for card in all_cards:
        card_counter += 1
        for info in card.values():
            price = int(info.get("price"))
            prices.append(price)

    average_price = sum(prices) / len(prices) if prices else 0
    median_price = statistics.median(prices) if prices else 0
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    return average_price, median_price, timestamp, card_counter


Monitoring(
    interval=60,
    environment='dev',
    debug=True,
    tenant='dev',
    stage='dev',
    repository_path='dev')


def main(driver, url):
    """ Основания функция """
    # Получение всех карточек
    all_cards = get_product_info(driver, url)
    # Формирование статистики
    average_price, median_price, timestamp, card_counter = get_statistic_info(all_cards)

    tags = {'role': 'application_family',
            'resource': 'Парсер авито',
            'method': 'check',
            'service': 'external_site',
            'average_price': average_price,
            'median_price': median_price,
            'timestamp': timestamp
            }
    # Фомрируем метрику
    Monitoring().graphite_metrics.add(
        metric='count.now',
        value=card_counter,
        tags=tags)
    Monitoring().graphite_metrics.send(debug=True)

    print(f"Средняя цена: {average_price}")
    print(f"Медианная цена: {median_price}")
    print(f"Timestamp: {timestamp}")


if __name__ == "__main__":
    URL = 'https://www.avito.ru/yaroslavl/kvartiry/sdam/posutochno/?s=104'
    driver_os = init_webdriver()
    main(driver_os, URL)
