import time
from tqdm import tqdm
import traceback
import datetime

from playwright.sync_api import Playwright, sync_playwright, expect
from bs4 import BeautifulSoup

from config import bcolors, send_logs_to_telegram


class OznData:
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
    send_logs_to_telegram(message=f'Finish: {t2}, TIME: {t2 - t1}')


if __name__ == '__main__':
    main()
