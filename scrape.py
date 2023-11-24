import os
import json
import pandas as pd
from io import StringIO

from playwright.sync_api import sync_playwright


def log_in(page):
    page.goto("https://www.learnedleague.com/")
    page.fill('#sidebar input[name="username"]', os.environ["LL_USER"])
    page.fill('#sidebar input[name="password"]', os.environ["LL_PASS"])
    page.click('#sidebar input[type="submit"]')


def get_urls(friend_id):
    base_url = "https://www.learnedleague.com/profiles.php?{id}".format(id=friend_id)
    urls = {"latest": base_url + "&1", "stats": base_url + "&2"}
    return urls


def scrape_latest_data(friend_id, data, page, url):
    page.goto(url)
    table = page.locator("div.fl_latest.fl_l_l.pldata").inner_html()
    dataframes = pd.read_html(StringIO(table))


def scrape_stats_data(friend_id, data, page, url):
    page.goto(url)
    table = page.locator(".statscontainer").inner_html()
    dataframes = pd.read_html(StringIO(table))


def scrape_friend_data(friend_id, data, page):
    for page_type, url in get_urls(friend_id).items():
        if page_type == "latest":
            scrape_latest_data(friend_id, data, page, url)
        elif page_type == "stats":
            scrape_stats_data(friend_id, data, page, url)


def scrape_data(friends):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        log_in(page)
        for friend_id, data in friends.items():
            scrape_friend_data(friend_id, data, page)


if __name__ == "__main__":
    with open("friends.json") as friends_file:
        friends = json.load(friends_file)
        scrape_data(friends)
