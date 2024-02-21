import os
import json
import pandas as pd
import numpy as np
import login
from io import StringIO
from colorama import Fore

from playwright.sync_api import sync_playwright


def get_player_categorical_stats(players, page):
    player_to_stats = {}
    for player_id in players:
        player_name = players[player_id]["name"]
        print(Fore.LIGHTMAGENTA_EX + f"Scraping categorical stats for {player_name}...")
        page.goto(f"https://www.learnedleague.com/profiles.php?{player_id}")
        table = page.locator("div.fl_latest.fl_l_l.pldata").inner_html()

        # We expect that there's only a single table on the page.
        df = pd.read_html(StringIO(table))[0]

        # Ignore columns specific to the current season, just look
        # at historical stats.
        df = df.filter(["Category", "Career", "%"])
        df.rename(columns={"%": "Percent Correct"}, inplace=True)

        # Drop totals, and sanitize categorical stats.
        df.drop(df[df["Category"] == "TOTALS"].index, inplace=True)
        df[["# Correct", "# Incorrect"]] = df["Career"].str.split("-", expand=True)
        df.drop(["Career"], axis=1, inplace=True)
        df.fillna(0, inplace=True)
        df.reset_index(inplace=True, drop=True)

        player_to_stats[player_id] = df
    return player_to_stats


def get_wins_losses_and_match_urls(players, page):
    unique_match_urls = set()
    player_wins_and_losses = {}
    for player_id in players:
        player_name = players[player_id]["name"]
        print(Fore.LIGHTCYAN_EX + f"Scraping match stats for {player_name}...")
        player_wins_and_losses[player_id] = {}
        page.goto(f"https://www.learnedleague.com/profiles.php?{player_id}&7")

        # Get all tables except the first, which isn't match data.
        tables = page.locator("div.fl_latest.fl_l_l").all()[1:]
        for t in tables:
            # This is of the form "LL#", where # is the season (e.g. "LL99")
            season = t.get_by_role("link").nth(0).inner_html()
            print(Fore.LIGHTMAGENTA_EX + f"...Scraping Season {season}")
            matches_df = pd.read_html(StringIO(t.inner_html()))[0][["Result"]]
            rundle = t.locator("h3").inner_text()[7:8]
            matches_df["Rundle"] = rundle
            opponent_flags = t.locator("a.flag").all()
            matches_df["Opponent"] = pd.Series(
                [flag.get_attribute("href").split("?")[1] for flag in opponent_flags]
            )
            player_wins_and_losses[player_id][season] = matches_df
            match_links = t.get_by_role("link").filter(has_text="Match Day").all()
            match_urls = [
                "https://www.learnedleague.com{match}".format(
                    match=l.get_attribute("href")
                )
                for l in match_links
            ]
            unique_match_urls.update(match_urls)

    return player_wins_and_losses, sorted(unique_match_urls)


def get_season_match_categories(match_urls, page):
    season_to_match_categories = {}
    cols = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
    for match_url in match_urls:
        _, season_and_match = match_url.split("?")
        season, match = season_and_match.split("&")
        print(
            Fore.LIGHTYELLOW_EX
            + f"Scraping question categories for LL{season}, match {match}..."
        )
        season_key = f"LL{season}"
        if season_key not in season_to_match_categories:
            season_to_match_categories[season_key] = pd.DataFrame(columns=cols)
        page.goto(match_url)

        questions = page.locator("div.ind-Q20.dont-break-out").all()
        row = pd.DataFrame(
            data=[
                (
                    text[3 : text.index(" -")]
                    for text in [question.inner_text() for question in questions]
                )
            ],
            columns=cols,
        )
        season_to_match_categories[season_key] = pd.concat(
            [season_to_match_categories[season_key], row]
        )
    return season_to_match_categories


def print_write_message(filename):
    print(Fore.LIGHTGREEN_EX + f"Writing file {filename}...")


def write_categorical_csv(player_name, categorical_stats_df):
    dir_path = f"data/{player_name}"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    categorical_stats = f"{dir_path}/categorical_stats.csv"
    print_write_message(categorical_stats)
    categorical_stats_df.to_csv(categorical_stats, index=False)


def write_win_loss_csvs(player_name, player_matches):
    dir_path = f"data/{player_name}"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    for season, matches_df in player_matches.items():
        season_matches = f"{dir_path}/{season}.csv"
        print_write_message(season_matches)
        matches_df.to_csv(season_matches, index=False)


def write_season_category_csv(season, match_categories_df):
    dir_path = f"data/seasons"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    match_categories = f"{dir_path}/match_categories_{season}.csv"
    print_write_message(match_categories)
    match_categories_df.to_csv(match_categories, index=False)


def scrape_and_write_data(players):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login.log_into_ll(page)

        categorical_stats = get_player_categorical_stats(players, page)
        [
            write_categorical_csv(
                players[player_id]["name"].lower(), categorical_stats_df
            )
            for player_id, categorical_stats_df in categorical_stats.items()
        ]

        wins_and_losses, match_urls = get_wins_losses_and_match_urls(players, page)
        [
            write_win_loss_csvs(players[player_id]["name"].lower(), player_matches)
            for player_id, player_matches in wins_and_losses.items()
        ]

        season_match_categories = get_season_match_categories(match_urls, page)
        [
            write_season_category_csv(season, match_categories_df)
            for season, match_categories_df in season_match_categories.items()
        ]

        browser.close()
    print(Fore.LIGHTGREEN_EX + "Scraping Finished!")


def scrape_player_ids_from_branches(branches):
    player_ids = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login.log_into_ll(page)
        for branch_id, data in branches.items():
            print(
                Fore.LIGHTMAGENTA_EX
                + "Scraping player IDs from branch: {}".format(data["name"])
            )
            page.goto(f"https://learnedleague.com/branch.php?{branch_id}")
            player_flags = page.locator("a.flag").all()
            for player_flag in player_flags:
                player_ids.add(player_flag.get_attribute("href").split("?")[1])
        browser.close()
    return player_ids


if __name__ == "__main__":
    # All of the players that we'll scrape data from, derived
    # from both explicit friends and members of requested branches.
    players = {}

    if os.path.exists("friends.json"):
        with open("friends.json") as friends_file:
            players = json.load(friends_file)

    branch_player_ids = set()
    if os.path.exists("branches.json"):
        with open("branches.json") as branches_file:
            branches = json.load(branches_file)
            branch_player_ids.update(scrape_player_ids_from_branches(branches))

    for player_id in branch_player_ids:
        if player_id not in players:
            players[player_id] = {"name": f"Player_{player_id}"}

    scrape_and_write_data(players)
