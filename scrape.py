import os
import json
import pandas as pd
from io import StringIO

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


def log_in(page):
    page.goto("https://www.learnedleague.com/")
    page.fill('#sidebar input[name="username"]', os.environ["LL_USER"])
    page.fill('#sidebar input[name="password"]', os.environ["LL_PASS"])
    page.click('#sidebar input[type="submit"]')


def get_urls_for_friend(friend_id):
    base_url = "https://www.learnedleague.com/profiles.php?{id}".format(id=friend_id)
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


def scrape_stats_data(page, url):
    """
    Returns a dataframe with the following columns:

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
        columns={
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
        },
        inplace=True,
    )

    # Drop the now unnecessary season column, and reindex
    # to account for dropped columns.
    df.drop(["Season"], axis=1, inplace=True)
    df.reset_index(inplace=True, drop=True)

    return df


def scrape_match_day_history(page, url, browser):
    """
    Returns a mapping of season names (e.g. "LL99") to dataframes
    representing the results for every match in that season, with
    the following columns:

    - Result: Representation of whether the player won (3), tied (2),
        lost (1), or forfeited (0).
    - Points: Total number of points the player scored.
    - Correct: Total number of questions answered correctly.
    - Opponent Points: Total number of points the opponent scored.
    - Opponent Correct: Total number of questions the opponend
        answered correctly.

    In the future this method will return more detailed statistics
    per match.
    """
    page.goto(url)

    # Mapping of seasons to dataframes with stats for that season.
    season_to_matches = {}

    # Get all tables except the first, which isn't match data.
    tables = page.locator("div.fl_latest.fl_l_l").all()[1:]
    for t in tables:
        # This is of the form "LL#", where # is the season (e.g. "LL99")
        season = t.get_by_role("link").nth(0).inner_html()

        # Collect high level match day data for the season
        df = pd.read_html(StringIO(t.inner_html()))[0]
        df.drop(["Match Day", "Opponent", "Record", "Rdl Rk"], axis=1, inplace=True)
        df["Result"].replace({"W": 3, "T": 2, "L": 1, "F": 0}, inplace=True)
        df["Result.1"] = df["Result.1"].str.replace(r"\(|\)-", " ", regex=True)
        df["Result.1"] = df["Result.1"].str.replace(")", "")
        df[["Points", "Correct", "Opponent Points", "Opponent Correct"]] = df[
            "Result.1"
        ].str.split(" ", expand=True)
        df["Correct"].replace({"F": 0}, inplace=True)
        df["Opponent Correct"].replace({"F": 0}, inplace=True)
        df.drop("Result.1", axis=1, inplace=True)

        season_to_matches[season] = df

        # Collect links of every match
        # links = t.get_by_role("link").filter(has_text=")-").all()
        # match_pages = [
        #     "https://www.learnedleague.com{match_selector}".format(
        #         match_selector=l.get_attribute("href")
        #     )
        #     for l in links
        # ]

        # # We need to create a new page here, otherwise the outer
        # # loop gets stuck.
        # new_page = browser.new_page()
        # log_in(new_page)
        # for match in match_pages:
        #     new_page.goto(match)

    return season_to_matches


def scrape_friend_data(friend_id, data, page, browser):
    friend_name = data["name"]
    for page_type, url in get_urls_for_friend(friend_id).items():
        if page_type == "latest":
            print("Scraping latest data for {friend}...".format(friend=friend_name))
            data["latest"] = scrape_latest_data(page, url)

        elif page_type == "stats":
            print("Scraping stats data for {friend}...".format(friend=friend_name))
            data["stats"] = scrape_stats_data(page, url)

        elif page_type == "past seasons":
            print("Scraping match data for {friend}...".format(friend=friend_name))
            data["season_to_matches"] = scrape_match_day_history(page, url, browser)


def scrape_data(friends):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        log_in(page)
        [
            scrape_friend_data(friend_id, data, page, browser)
            for friend_id, data in friends.items()
        ]
    print("Scraping Finished!")


def print_write_message(filename):
    print("Writing file {filename}...".format(filename=filename))


def write_csvs(friend):
    name = friend["name"].lower()
    dir_path = "data/{name}".format(name=name)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    latest_stats = "{dir}/latest_league_stats.csv".format(dir=dir_path)
    print_write_message(latest_stats)
    friend["latest"].to_csv(latest_stats, sep="\t", encoding="utf-8")

    overall_stats = "{dir}/overall_league_stats.csv".format(dir=dir_path)
    print_write_message(overall_stats)
    friend["stats"].to_csv(overall_stats, sep="\t", encoding="utf-8")

    for season, match_stats_df in friend["season_to_matches"].items():
        season_path = "{dir}/{season}".format(dir=dir_path, season=season)
        if not os.path.exists(season_path):
            os.makedirs(season_path)

        season_stats = "{dir}/season_stats.csv".format(dir=season_path)
        print_write_message(season_stats)
        match_stats_df.to_csv(season_stats, sep="\t", encoding="utf-8")


if __name__ == "__main__":
    with open("friends.json") as friends_file:
        friends = json.load(friends_file)
        scrape_data(friends)
        [write_csvs(data) for _, data in friends.items()]
