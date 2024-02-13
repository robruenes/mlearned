import os


def log_into_ll(page):
    page.goto("https://www.learnedleague.com/")
    page.fill('#sidebar input[name="username"]', os.environ["LL_USER"])
    page.fill('#sidebar input[name="password"]', os.environ["LL_PASS"])
    page.click('#sidebar input[type="submit"]')
