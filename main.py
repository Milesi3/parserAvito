from expmonitoring import Monitoring
from selenium import webdriver
from selenium_stealth import stealth
import time
from bs4 import BeautifulSoup
import statistics


def init_webdriver():
    driver = webdriver.Chrome()
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine"
            )
    return driver


def get_product_info(driver, url):
    driver.get(url)
    main_page_html = BeautifulSoup(driver.page_source, "lxml")

    content = main_page_html.find("div", {"data-marker": "catalog-serp"})
    cards = content.findChildren(recursive=False)

    all_cards = list()
    number_cards = 0
    for card in cards:
        card_name = card.find("a", title=True)["title"]
        card_url = card.find("a", href=True)["href"]
        product_url = "https://www.avito.ru" + card_url

        time_card = get_time_info(driver, product_url)
        if "вчера" not in time_card:
            return all_cards
        time_card = f'{time.strftime("%Y-%m-%d")} {str(time_card.split(" ")[2])}'

        try:
            price = card.find("p", {"data-marker": "item-price"}).findChildren(recursive=False)[1]["content"]
            card_info = {number_cards: {"name": card_name,
                                        "url": product_url,
                                        "price": price,
                                        "time": time_card
                                        }
                         }
            all_cards.append(card_info)
            number_cards += 1
        except:
            print('Вонючий банер был отсеян')
    return all_cards


def get_time_info(driver, product_url):
    driver.get(product_url)
    card_page_html = BeautifulSoup(driver.page_source, "lxml")
    time_card = (card_page_html.find("span", {"data-marker": "item-view/item-date"})
                 .text.replace(" · ", ""))
    return time_card

def get_statistic_info(all_cards):
    prices = []
    card_counter = 0
    for card in all_cards:
        card_counter += 1
        for info in card.values():
            price = int(info.get("price"))
            prices.append(price)

    average_price = sum(prices) / len(prices) if prices else 0
    median_price = statistics.median(prices) if prices else 0
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    return average_price, median_price, timestamp, card_counter

Monitoring(interval=60, environment='dev', debug=True, tenant='dev', stage='dev', repository_path='dev')
def main(driver, url):

    all_cards = get_product_info(driver, url)
    average_price, median_price, timestamp, card_counter = get_statistic_info(all_cards)

    tags = {'role': 'application_family',
            'resource': 'Парсер авито',
            'method': 'check',
            'service': 'external_site',
            'average_price': average_price,
            'median_price': median_price,
            'timestamp': timestamp
            }

    Monitoring().graphite_metrics.add(
                            metric='count.now',
                            value=card_counter,
                            tags=tags)
    Monitoring().graphite_metrics.send(debug=True)

    print(f"Средняя цена: {average_price}")
    print(f"Медианная цена: {median_price}")
    print(f"Timestamp: {timestamp}")

if __name__ == "__main__":
    url = 'https://www.avito.ru/yaroslavl/kvartiry/sdam/posutochno/?s=104'
    driver = init_webdriver()
    main(driver, url)



