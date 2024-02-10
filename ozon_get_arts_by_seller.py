"""Скрипт открывает страницу продавца и проходит по всем страницам, забирая ссылки на товар"""

import time
from tqdm import tqdm
import traceback

import datetime
from playwright.sync_api import Playwright, sync_playwright, expect
from bs4 import BeautifulSoup

from config import SELLER_URL, bcolors


class Ozn:
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

    def get_data_by_page(self, art):
        pass

    def undetectable(self):
        """Переходим на страницу, обходим блокировку"""
        # url = f'https://bot.sannysoft.com'
        url = f'https://ozon.ru'
        self.page.goto(url, timeout=30000)
        # button = self.page.locator('//*[@id="reload-button"]')
        # Ожидание появления кнопки с id="reload-button"
        button_locator = '//*[@id="reload-button"]'
        self.page.wait_for_selector(button_locator)
        # Теперь можно получить элемент
        button = self.page.locator(button_locator)
        if button:
            button.click()
        # self.page.goto('https://www.ozon.ru/seller/forward-zoo-1574061/tovary-dlya-zhivotnyh-12300/?miniapp=seller_1574061')
        # self.page.locator('//*[@id="layoutPage"]/div[1]/div[5]/div/div/div[2]/div[3]')
        time.sleep(5)

    def check_last_page(self):
        soup = BeautifulSoup(self.page.content(), 'lxml')
        no_data = soup.find('div', class_='yv4', attrs={'data-widget': 'searchResultsError'})
        if no_data:
            return False
        else:
            return True

    def get_arts_by_seller_page(self):
        """Перебор по ссылкам на товары магазина, получение списка url на товары"""
        retry_count = 3
        start_page = 1
        finish_page_flag = True
        while retry_count > 0 or finish_page_flag:
            try:
                self.page.goto(f'{SELLER_URL}&page={start_page}')
                start_page += 1
                finish_page_flag = self.check_last_page()
            except Exception as exp:
                traceback_str = traceback.format_exc()
                print(f'{bcolors.WARNING}Ошибка при загрузке страницы {SELLER_URL}&page={start_page}: {bcolors.ENDC}'
                      f'\n{str(exp)}\n\n'
                      f'{traceback_str}')
                retry_count -= 1
                if retry_count > 0:
                    print(f'Повторная попытка загрузить страницу ({retry_count} осталось)')
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
            Ozn(playwright=playwright).start()
        print(f'Успешно')
    except Exception as exp:
        print(exp)
    t2 = datetime.datetime.now()
    print(f'Finish: {t2}, TIME: {t2 - t1}')
    # send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()
