import os
import json
import pandas as pd
import numpy as np
import login
from io import StringIO
from colorama import Fore

from playwright.sync_api import sync_playwright


def transform_rundle_value(rundle):
    rundle_mapping = {
        "R": 0,  # Rookie season
        "E": 1,  # Lowest regular season rundle
        "D": 2,
        "C": 3,
        "B": 4,
        "A": 5,  # Highest regular season rundle
    }
    return rundle_mapping[rundle[0]]


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


def renamed_stats_columns():
    return {
        "W": "Wins",
        "L": "Losses",
        "T": "Ties",
        "PTS": "Points in Standings",
        "MPD": "Match Points Differential",
        "TMP": "Total Match Points",
        "TCA": "Total Correct Answers",
        "TPA": "Total Points Allowed",
        "CAA": "Correct Answers Allowed",
        "UfPA": "Unforced Points Allowed",
        "DE": "Defensive Efficiency",
        "FW": "Wins by Forfeit",
        "FL": "Losses by Forfeit",
        "3PT": "3 point questions answered correctly",
    }


def get_urls_for_player(player_id):
    base_url = f"https://www.learnedleague.com/profiles.php?{player_id}"
    urls = {
        "latest": base_url + "&1",
        "stats": base_url + "&2",
        "past seasons": base_url + "&7",
    }
    return urls


def scrape_latest_data(page, url):
    """
    Returns a dataframe with the following columns:

    - Category: The category of the question, using the numerical representation
        from the method `transform_category_value` above.
    - Percent Correct: The percentage of questions of this category the player has answered correctly.
    - Num Correct: Total number of questions in this category answered correctly.
    - Num Incorrect: Total number of questions in this category answered incorrectly.
    """

    page.goto(url)
    table = page.locator("div.fl_latest.fl_l_l.pldata").inner_html()

    # We expect that there's only a single table on the page.
    df = pd.read_html(StringIO(table))[0]

    # Ignore columns specific to the current season, just look
    # at historical stats.
    df = df.filter(["Category", "Career", "%"])
    df.rename(columns={"%": "Percent Correct"}, inplace=True)

    # Drop totals, and sanitize categorical stats.
    df.drop(df[df["Category"] == "TOTALS"].index, inplace=True)
    df["Category"] = df["Category"].transform(transform_category_value)
    df.sort_values(by=["Category"], inplace=True)
    df[["Num Correct", "Num Incorrect"]] = df["Career"].str.split("-", expand=True)
    df.drop(["Career"], axis=1, inplace=True)
    df.reset_index(inplace=True, drop=True)

    return df


def scrape_season_stats_data(page, url):
    """
    Returns a dataframe with one row per season,
    with the following columns:

    - Wins: Total number of wins across all player history.
    - Losses: Total number of losses across all player history.
    - Ties: Total number of ties across all player history.
    - Points in Standings: Determines where the player is in overall
        standings. 2 points for win, 1 for tie, -1 for forfeit.
    - Match Points Differential: Difference between points scored and
        points allowed.
    - Total Match Points: Sum of points scored in all matches.
    - Total Correct Answers: Sum of questions answered correctly
        in all matches.
    - Total Points Allowed: Sum of points scored by opponents in all matches.
    - Correct Answers Allowed: Total number of questions answered correctly
        by opponents in all matches.
    - Unforced Points Allowed: Total number of points allowed above that
        which would have been allowed with perfect defense.
    - Defensive Efficiency: Measure of how good the player is defensively.
        The higher the better.
    - Wins by Forfeit: Self explanatory.
    - Losses by Forfeit: Self explanatory.
    - 3 point questions answered correctly: Self explanatory.
    - Rundle: The rundle the player competed in, as a measure of average opponent
        difficulty, using the representation from `transform_rundle_value` above.
    """

    page.goto(url)
    table = page.locator(".statscontainer").inner_html()
    df = pd.read_html(StringIO(table))[0]

    # Remove columns we don't need (Rank), or which don't have a clear
    # explanation found on the site (PCAA, MCW, QPct)
    df.drop(["Rank", "PCAA", "MCW", "QPct"], axis=1, inplace=True)

    # Drop career and per-rundle aggregated statistics.
    df = df[df["Season"].map(lambda season: season.startswith("LL"))]

    # Transform the rundle string into a numerical value.
    df["Rundle"] = df["Rundle"].transform(transform_rundle_value)

    df.rename(
        columns=renamed_stats_columns(),
        inplace=True,
    )

    # Drop the now unnecessary season column, and reindex
    # to account for dropped columns.
    df.drop(["Season"], axis=1, inplace=True)
    df.reset_index(inplace=True, drop=True)

    return df


def scrape_career_stats_data(page, url):
    """
    Returns a dataframe with the same columns
    as scrape_season_stats_data, but with the stats
    for the player's overall career.
    """
    page.goto(url)
    table = page.locator(".statscontainer").inner_html()
    df = pd.read_html(StringIO(table))[0]

    # Remove columns we don't need (Season,Rank), or which don't have a clear
    # explanation found on the site (PCAA, MCW, QPct)
    df.drop(["Season", "Rank", "PCAA", "MCW", "QPct"], axis=1, inplace=True)

    # Drop everything but the career row.
    # Drop career and per-rundle aggregated statistics.
    df = df[df["Rundle"].map(lambda rundle: rundle == "Career")]

    # At this point, we don't need that column anymore.
    df.drop(["Rundle"], axis=1, inplace=True)
    df.rename(
        columns=renamed_stats_columns(),
        inplace=True,
    )
    df.reset_index(inplace=True, drop=True)
    return df


def matches_df_from_table(t):
    matches_df = pd.read_html(StringIO(t.inner_html()))[0][["Result"]]
    matches_df["Result"] = matches_df["Result"].replace(
        {"W": "1", "T": "0", "L": "-1", "F": "-2"}
    )
    matches_df["Result"] = matches_df["Result"].str[0]
    # The string containing the rundle is formed like "Rundle C Sugarloaf Div 1"
    # so we just grab the exact char we need out of it.
    rundle = t.locator("h3").inner_text()[7:8]
    matches_df["Rundle"] = transform_rundle_value(rundle)
    return matches_df


def set_and_cache_question_counts(
    browser, matches_df, match_pages, season, season_match_category_cache
):
    # We need to create a new page here, otherwise the outer
    # loop in scrape_match_day_history gets stuck
    new_page = browser.new_page()
    login.log_into_ll(new_page)

    zeros = np.zeros(len(matches_df), dtype=int)
    question_counts = {
        "AMER HIST": zeros,
        "ART": zeros,
        "BUS/ECON": zeros,
        "CLASS MUSIC": zeros,
        "CURR EVENTS": zeros,
        "FILM": zeros,
        "FOOD/DRINK": zeros,
        "GAMES/SPORT": zeros,
        "GEOGRAPHY": zeros,
        "LANGUAGE": zeros,
        "LIFESTYLE": zeros,
        "LITERATURE": zeros,
        "MATH": zeros,
        "POP MUSIC": zeros,
        "SCIENCE": zeros,
        "TELEVISION": zeros,
        "THEATRE": zeros,
        "WORLD HIST": zeros,
    }
    matches_df = matches_df.assign(**question_counts)
    for i, match in enumerate(match_pages):
        print(Fore.LIGHTYELLOW_EX + f"....Scraping question categories for match {i}")
        new_page.goto(match)
        question_categories = (
            pd.read_html(StringIO(new_page.inner_html("body")))[2][
                ["Question/Answer.1"]
            ][:6]
            .astype("string")
            .apply(lambda s: s.str.split(" —").str.get(0), axis=1)
            .to_numpy()
            .flatten()
        )

        for category in question_categories:
            matches_df.at[i, category] = matches_df.at[i, category] + 1

    cached_match_df = matches_df.copy(deep=True)
    cached_match_df.drop(columns=["Result", "Rundle"], inplace=True)
    season_match_category_cache[season] = cached_match_df


def scrape_match_day_history(page, url, browser, season_match_category_cache):
    """
    Returns a mapping of season names (e.g. "LL99") to dataframes
    representing the results for every match in that season, with
    the following columns:

    - Result: Representation of whether the player won (3), tied (2),
        lost (1), or forfeited (0).
    - Columns for each of categories, counting how many questions in a
        given day belonged to that category.
    """
    page.goto(url)

    # Mapping of seasons to dataframes with stats for that season.
    season_to_matches = {}

    # Get all tables except the first, which isn't match data.
    tables = page.locator("div.fl_latest.fl_l_l").all()[1:]
    for t in tables:
        # This is of the form "LL#", where # is the season (e.g. "LL99")
        season = t.get_by_role("link").nth(0).inner_html()
        print(Fore.LIGHTMAGENTA_EX + f"...Scraping Season {season}")

        matches_df = matches_df_from_table(t)

        # Collect links of every match
        links = t.get_by_role("link").filter(has_text=")-").all()
        match_pages = [
            "https://www.learnedleague.com{match_selector}".format(
                match_selector=l.get_attribute("href")
            )
            for l in links
        ]

        if season not in season_match_category_cache:
            set_and_cache_question_counts(
                browser, matches_df, match_pages, season, season_match_category_cache
            )

        else:
            print(
                Fore.LIGHTGREEN_EX
                + f"....Already have question categories for all {season} matches"
            )

        matches_df = matches_df.assign(**season_match_category_cache[season])
        season_to_matches[season] = matches_df

    return season_to_matches


def scrape_player_data(player_id, data, page, browser, season_match_category_cache):
    player_name = data["name"]
    for page_type, url in get_urls_for_player(player_id).items():
        if page_type == "latest":
            print(Fore.LIGHTCYAN_EX + f"Scraping latest data for {player_name}...")
            data["latest"] = scrape_latest_data(page, url)

        elif page_type == "stats":
            print(Fore.LIGHTCYAN_EX + f"Scraping stats data for {player_name}...")
            data["season_stats"] = scrape_season_stats_data(page, url)
            data["career_stats"] = scrape_career_stats_data(page, url)

        elif page_type == "past seasons":
            print(Fore.LIGHTCYAN_EX + f"Scraping match data for {player_name}...")
            data["season_to_matches"] = scrape_match_day_history(
                page, url, browser, season_match_category_cache
            )


def scrape_data_from_players(players):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        season_match_category_cache = {}
        login.log_into_ll(page)
        [
            scrape_player_data(
                player_id, data, page, browser, season_match_category_cache
            )
            for player_id, data in players.items()
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


def print_write_message(filename):
    print(Fore.LIGHTGREEN_EX + f"Writing file {filename}...")


def write_csvs(player):
    name = player["name"].lower()
    dir_path = f"data/{name}"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    latest_stats = f"{dir_path}/latest_league_stats.csv"
    print_write_message(latest_stats)
    player["latest"].to_csv(latest_stats, sep="\t", encoding="utf-8", index=False)

    season_stats = f"{dir_path}/per_season_stats.csv"
    print_write_message(season_stats)
    player["season_stats"].to_csv(season_stats, sep="\t", encoding="utf-8", index=False)

    career_stats = f"{dir_path}/career_stats.csv"
    print_write_message(career_stats)
    player["career_stats"].to_csv(career_stats, sep="\t", encoding="utf-8", index=False)

    for season, match_stats_df in player["season_to_matches"].items():
        match_stats = f"{dir_path}/match_stats_{season}.csv"
        print_write_message(match_stats)
        match_stats_df.to_csv(match_stats, sep="\t", encoding="utf-8", index=False)


if __name__ == "__main__":
    # All of the players that we'll scrape data from, derived
    # from both explicit friends and members of requested branches.
    players = {}

    with open("friends.json") as friends_file:
        players = json.load(friends_file)

    branch_player_ids = set()
    with open("branches.json") as branches_file:
        branches = json.load(branches_file)
        branch_player_ids.update(scrape_player_ids_from_branches(branches))

    for player_id in branch_player_ids:
        if player_id not in players:
            players[player_id] = {"name": f"Player_{player_id}"}

    scrape_data_from_players(players)
    [write_csvs(data) for _, data in players.items()]
