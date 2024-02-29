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
        """Извлекаем первую часть данных из JSON"""
        script_tag = soup.find('script', {'type': 'application/ld+json'})
        # Получаем содержимое тега <script>
        script_content = script_tag.contents[0] if script_tag else None
        # Парсим JSON-данные
        data = json.loads(script_content) if script_content else None
        # Список ключей, которые нужно извлечь в новый словарь
        desired_keys = ['name', 'sku', 'brand', 'description', 'offers.price', 'aggregateRating.ratingValue',
                        'aggregateRating.reviewCount']
        filtered_dict = {key: reduce(lambda d, k: d.get(k, {}), key.split('.'), data) for key in desired_keys}
        "Извлекаем описание"
        # Найдем блок с описанием товара
        description_section = soup.find('div', id='section-description')
        allspan = set([x.text.strip() for x in description_section.find_all('span')])
        # Извлечем текст из всех тегов <span> внутри блока с описанием
        description_text = '. '.join(span for span in allspan)
        "Извлекаем характеристики"
        # Находим блок с характеристиками
        characteristics_block = soup.find('div', {'id': 'section-characteristics'})
        # Инициализируем пустой словарь для характеристик
        characteristics_dict = {}
        # Найдем все теги <dl> внутри блока с характеристиками, которые отвечают за пары характеристик
        dl_tags = characteristics_block.find_all('dl')
        for dl_tag in dl_tags:
            dt_tag = dl_tag.find('dt')
            dd_tag = dl_tag.find('dd')
            if dt_tag and dd_tag:
                characteristic_name = dt_tag.text.strip()
                characteristic_value = dd_tag.text.strip()
                characteristics_dict[characteristic_name] = characteristic_value
        "Объединяем словари"
        filtered_dict['characteristics'] = characteristics_dict
        filtered_dict['description_main'] = description_text
        "Находим изображения"
        # Найти все div с классом 'jq4'
        divs_with_images = soup.find_all('div', class_='jq4')
        # Извлечь ссылки на изображения из каждого найденного div
        image_links = [div.find('img')['src'] for div in divs_with_images]
        image_large_links = list(set([x.replace('wc50', 'wc1000') for x in image_links]))
        filtered_dict['imgs'] = image_large_links
        sku = filtered_dict.get('sku')
        "Добавляем результирующий словарь в итоговый на основе SKU"
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
