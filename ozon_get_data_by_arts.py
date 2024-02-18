import time
from tqdm import tqdm
import traceback
import datetime
import json
from functools import reduce

from playwright.sync_api import Playwright, sync_playwright, expect
from bs4 import BeautifulSoup

from config import bcolors, send_logs_to_telegram


def read_articles_from_txt():
    """Считывает и возвращает список ссылок на товары из файла"""
    with open('out/urls_articles.txt', 'r', encoding='utf-8') as file:
        articles = [f'{line}'.rstrip() for line in file]
    return articles


class OznData:
    playwright = None
    browser = None
    page = None
    context = None
    res_dict = {}

    def __init__(self, playwright):
        self.playwright_config(playwright=playwright)

    def playwright_config(self, playwright):
        js = """
        Object.defineProperties(navigator, {webdriver:{get:()=>undefined}});
        """
        self.playwright = playwright
        self.browser = playwright.chromium.launch(headless=False, args=['--blink-settings=imagesEnabled=false'])
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.add_init_script(js)

    def get_soup(self):
        soup = BeautifulSoup(self.page.content(), 'lxml')
        return soup

    def undetectable(self):
        """Переходим на страницу, обходим блокировку"""
        # url = f'https://bot.sannysoft.com'
        url = f'https://ozon.ru'
        self.page.goto(url, timeout=30000)
        # Ожидание появления кнопки с id="reload-button"
        button_locator = '//*[@id="reload-button"]'
        try:
            # Теперь можно получить элемент
            button = self.page.wait_for_selector(button_locator, timeout=3000)
            button.click()
            print(f'{bcolors.WARNING}Нашли кнопку ОБНОВИТЬ и нажимаем на нее{bcolors.ENDC}')
        except:
            print(f'{bcolors.OKGREEN}Кнопки ОБНОВИТЬ нет на странице{bcolors.ENDC}')
        time.sleep(2)

    def save_data_from_soup(self, soup):
        """Извлекаем первую часть данных"""
        script_tag = soup.find('script', {'type': 'application/ld+json'})
        # Получаем содержимое тега <script>
        script_content = script_tag.contents[0] if script_tag else None
        # Парсим JSON-данные
        data = json.loads(script_content) if script_content else None
        # Список ключей, которые нужно извлечь в новый словарь
        desired_keys = ['name', 'sku', 'brand', 'description', 'offers.price', 'aggregateRating.ratingValue',
                        'aggregateRating.reviewCount']
        filtered_dict = {key: reduce(lambda d, k: d.get(k, {}), key.split('.'), data) for key in desired_keys}
        "Извлекаем характеристики"
        # Находим блок с характеристиками
        characteristics_block = soup.find('div', {'id': 'section-characteristics'})
        # Инициализируем пустой словарь для характеристик
        characteristics_dict = {}
        # Если блок с характеристиками существует
        if characteristics_block:
            # Находим все элементы dl с классом 'j4v' внутри блока характеристик
            for dl_elem in characteristics_block.find_all('dl', {'class': 'j4v'}):
                # Извлекаем текст из элементов dt и dd
                key = dl_elem.find('dt', {'class': 'j3v'}).span.text.strip()
                value = dl_elem.find('dd', {'class': 'vj3'}).text.strip()
                # Добавляем пару ключ-значение в словарь характеристик
                characteristics_dict[key] = value
        "Объединяем словари"
        filtered_dict['characteristics'] = characteristics_dict
        sku = filtered_dict.get('sku')
        "Добавляем результирующи словарь в итоговый на основе SKU"
        self.res_dict[sku] = filtered_dict
        "Записываем результат в json"
        with open('out/ozon_data.json', 'w', encoding='utf-8') as json_file:
            json.dump(self.res_dict, json_file, indent=2, ensure_ascii=False)

    def get_data_by_arts(self, articles):
        """Перебор по ссылкам на товары, получение данных"""
        for art in tqdm(articles):
            retry_count = 3
            while retry_count > 0:
                try:
                    self.page.goto(f'{art}?oos_search=false', timeout=30000)
                    time.sleep(5)
                    soup = self.get_soup()
                    self.save_data_from_soup(soup)
                    break
                except Exception as exp:
                    traceback_str = traceback.format_exc()
                    print(
                        f'{bcolors.WARNING}Ошибка при загрузке страницы:{bcolors.ENDC}\n{art}\n'
                        f'\n{str(exp)}\n\n'
                        f'{traceback_str}')
                    retry_count -= 1
                    if retry_count > 0:
                        print(f'{bcolors.WARNING}Повторная попытка загрузить страницу:{bcolors.ENDC}\n{art}\n'
                              f'Попыток осталось: {retry_count}')
                    else:
                        print(f'{bcolors.FAIL}Превышено количество попыток загрузить страницу:{bcolors.ENDC}'
                              f'\n{art}')
                        break

    def start(self):
        self.undetectable()
        articles = read_articles_from_txt()
        self.get_data_by_arts(articles)


def main():
    t1 = datetime.datetime.now()
    print(f'Start: {t1}')
    try:
        with sync_playwright() as playwright:
            OznData(playwright=playwright).start()
        print(f'Успешно')
    except Exception as exp:
        print(exp)
    t2 = datetime.datetime.now()
    print(f'Finish: {t2}, TIME: {t2 - t1}')
    # send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()
