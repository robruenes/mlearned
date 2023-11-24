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


def transform_category_value(category):
    category_mapping = {
        "AMER HIST": 0,
        "ART": 1,
        "BUS/ECON": 2,
        "CLASS MUSIC": 3,
        "CURR EVENTS": 4,
        "FILM": 5,
        "FOOD/DRINK": 6,
        "GAMES/SPORT": 7,
        "GEOGRAPHY": 8,
        "LANGUAGE": 9,
        "LIFESTYLE": 10,
        "LITERATURE": 11,
        "MATH": 12,
        "POP MUSIC": 13,
        "SCIENCE": 14,
        "TELEVISION": 15,
        "THEATRE": 16,
        "WORLD HIST": 17,
    }
    return category_mapping[category]


def scrape_latest_data(friend_id, data, page, url):
    page.goto(url)
    table = page.locator("div.fl_latest.fl_l_l.pldata").inner_html()
    df = pd.read_html(StringIO(table))[0]
    categorical = df[df["Category"].map(lambda category: category != "TOTALS")]
    categorical["Category"] = categorical["Category"].transform(
        transform_category_value
    )
    # TODO: Decide how this will be stored, and doing something
    # with the TOTALS row might be useful.


def transform_rundle_value(rundle):
    rundle_mapping = {
        "R": 1,
        "E": 1,
        "D": 2,
        "C": 3,
        "B": 4,
        "A": 5,
    }
    return rundle_mapping[rundle[0]]


def scrape_stats_data(friend_id, data, page, url):
    page.goto(url)
    table = page.locator(".statscontainer").inner_html()
    df = pd.read_html(StringIO(table))[0]

    # Remove the rank column.
    df.drop(["Rank"], axis=1, inplace=True)

    # Drop career and per-rundle aggregated statistics.
    df = df[df["Season"].map(lambda season: season.startswith("LL"))]

    # Transform the rundle string into a numerical value.
    df["Rundle"] = df["Rundle"].transform(transform_rundle_value)

    # Drop the now unnecessary season column, and reindex
    # to account for dropped columns.
    df.drop(["Season"], axis=1, inplace=True)
    df.reset_index(inplace=True)
    # TODO: Decide how we'll ultimately store this,
    # and limit to the same number of rows per player.


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
