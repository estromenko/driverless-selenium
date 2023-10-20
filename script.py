import time

import cdp
from bs4 import BeautifulSoup

from driverless_selenium import Chrome

city_selector = "div.i-pl20 span"

brand_splitting_pages = []


class Soup:
    """Обертка для BeautifulSoup."""

    def __init__(self, document) -> None:
        self.soup = BeautifulSoup(document, "lxml")

    def select(self, css_selectors):
        """Выборка из элементов в Soup'e."""
        if isinstance(css_selectors, list):
            res = None
            for selector in css_selectors:
                res = self.soup.select(selector)
                if res:
                    return res

            return res

        return self.soup.select(css_selectors)


def make_soup(document=""):
    """Создает Soup (объект переопределенного класса Beautiful Soup) из указанной страницы."""
    return Soup(document if document else browser.page_source)


def get_element_attr(css_selector, attr_name, index=0):
    escaped_selector = css_selector.replace('"', '\\"')
    return browser.execute_script(
        f'return document.querySelectorAll("{escaped_selector}")[{index}].'
        f'getAttribute("{attr_name}");')


def get_element_text(css_selector, index=0):
    escaped_selector = css_selector.replace('"', '\\"')
    javascript = f'return document.querySelectorAll("{escaped_selector}")[{index}]'
    text = browser.execute_script(javascript + ".firstChild.textContent;").strip()
    if text:
        return text

    return browser.execute_script(javascript + ".text")


def go_through_ordinary_catalog(css_selector):
    links = make_soup().select(css_selector)
    links_number = len(links)
    for link_n in range(links_number):
        get_element_attr(css_selector, "href", link_n)
        get_element_text(css_selector, link_n)

    print(links_number)
    return links_number


with Chrome() as browser:
    browser.get("https://www.komus.ru/katalog/c/0/")
    time.sleep(4)
    node_id = browser.find_by_css(city_selector)[0]
    browser.click(node_id)
    time.sleep(3)

    regions = browser.find_by_css('li.b-region__list__item > a > span')
    for region in regions:
        print(region)
        if "Ростовская область" in browser.get_html(region):
            browser.click(region)
            break
    time.sleep(1000)
