"""Скрипт открывает страницу продавца и проходит по всем страницам, забирая ссылки на товар в файл urls_articles.txt"""

import time
import traceback

import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from config import SELLER_URL, bcolors, send_logs_to_telegram


def write_url(links):
    with open('out/urls_articles.txt', 'a') as file:
        file.writelines(link + '\n' for link in links)


class OznArts:
    playwright = None
    browser = None
    page = None
    context = None

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

    def get_urls_by_page(self, soup):
        mega_paginator = soup.find('div', class_='pe1', attrs={'data-widget': 'megaPaginator'})
        links = [link['href'] for link in mega_paginator.find_all('a', href=True) if link['href'].startswith('/product/')]
        links = set([f'https://ozon.ru{x.split("?")[0]}' for x in links])
        write_url(links)

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

    def check_last_page(self, soup):
        zv = soup.find('div', class_='zv')
        # no_data = soup.find('div', class_='yv4', attrs={'data-widget': 'searchResultsError'})
        if zv:
            return False
        else:
            return True

    def get_arts_by_seller_page(self):
        """Перебор по ссылкам на товары магазина, получение списка url на товары"""
        retry_count = 3
        start_page = 1
        while retry_count > 0:
            try:
                self.page.goto(f'{SELLER_URL}&page={start_page}', timeout=3000)
                time.sleep(5)
                soup = self.get_soup()
                self.get_urls_by_page(soup)
                finish_page_flag = self.check_last_page(soup)
                if finish_page_flag:
                    print(f'Страница {start_page} успешно отработана')
                    start_page += 1
                elif finish_page_flag is False:
                    print(f'{bcolors.WARNING}Страница {start_page} уже не существует, завершаем работу.{bcolors.ENDC}')
                    break
            except Exception as exp:
                traceback_str = traceback.format_exc()
                print(f'{bcolors.WARNING}Ошибка при загрузке страницы {SELLER_URL}&page={start_page}: {bcolors.ENDC}'
                      f'\n{str(exp)}\n\n'
                      f'{traceback_str}')
                retry_count -= 1
                if retry_count > 0:
                    print(f'{bcolors.WARNING}Повторная попытка загрузить страницу ({retry_count} осталось)'
                          f'{bcolors.ENDC}')
                else:
                    print(f'{bcolors.FAIL}Превышено количество попыток для страницы:{bcolors.ENDC}'
                          f'\n{SELLER_URL}&page={start_page}')
                    break

    def start(self):
        self.undetectable()
        self.get_arts_by_seller_page()


def main():
    t1 = datetime.datetime.now()
    print(f'Start: {t1}')
    try:
        with sync_playwright() as playwright:
            OznArts(playwright=playwright).start()
        print(f'Успешно')
    except Exception as exp:
        print(exp)
    t2 = datetime.datetime.now()
    print(f'Finish: {t2}, TIME: {t2 - t1}')
    send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()
