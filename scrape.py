import os
import json

from playwright.sync_api import sync_playwright


def log_in(page):
    page.goto("https://www.learnedleague.com/")
    page.fill('#sidebar input[name="username"]', os.environ["LL_USER"])
    page.fill('#sidebar input[name="password"]', os.environ["LL_PASS"])
    page.click('#sidebar input[type="submit"]')


def scrape_friend_data(friend, data, page):
    friend_id = data["id"]
    page.goto("https://www.learnedleague.com/profiles.php?{id}".format(id=friend_id))


def scrape_data(friends):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        log_in(page)
        for friend, data in friends.items():
            scrape_friend_data(friend, data, page)


if __name__ == "__main__":
    with open("friends.json") as friends_file:
        friends = json.load(friends_file)
        scrape_data(friends)
