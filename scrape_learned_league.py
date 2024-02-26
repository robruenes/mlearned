import argparse
import glob
import json
import login
import os
import pandas as pd

from io import StringIO
from colorama import Fore

from playwright.sync_api import sync_playwright, TimeoutError


def scrape_categorical_stats_df(player_id, player_name, page):
    print(Fore.LIGHTMAGENTA_EX + f"Scraping categorical stats for {player_name}...")
    page.goto(f"https://www.learnedleague.com/profiles.php?{player_id}")

    try:
        table = page.locator("div.fl_latest.fl_l_l.pldata").inner_html(timeout=2000)
    except TimeoutError:
        print(Fore.LIGHTRED_EX + f"Timed out, player {player_id} is likely inactive.")
        return None

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
    return df


def scrape_wins_losses_and_match_urls(
    player_id, player_name, season_to_match_urls, page
):
    wins_and_losses = {}

    print(Fore.LIGHTCYAN_EX + f"Scraping match stats for {player_name}...")
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
        wins_and_losses[season] = matches_df

        if season not in season_to_match_urls:
            match_links = t.get_by_role("link").filter(has_text="Match Day").all()
            season_to_match_urls[season] = [
                "https://www.learnedleague.com{match}".format(
                    match=l.get_attribute("href")
                )
                for l in match_links
            ]

    return wins_and_losses


def scrape_season_match_categories(season_match_urls, page):
    cols = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
    df = pd.DataFrame(columns=cols)
    for match_url in season_match_urls:
        _, season_and_match = match_url.split("?")
        season, match = season_and_match.split("&")
        # TODO: Update logic to handle seasons from 59 and down, which don't
        # have the same page structure.
        print(
            Fore.LIGHTYELLOW_EX
            + f"Scraping question categories for LL{season}, match {match}..."
        )
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
        df = pd.concat([df, row])
    return df


def print_write_message(filename):
    print(Fore.LIGHTGREEN_EX + f"Writing file {filename}...")


def write_win_loss_csvs(dir_path, player_matches):
    for season, matches_df in player_matches.items():
        season_matches = f"{dir_path}/{season}.csv"
        print_write_message(season_matches)
        matches_df.to_csv(season_matches, index=False)


def scrape_and_write_per_player_data(players, check_files, season_to_match_urls, page):
    for player_id in players:
        player_name = players[player_id]["name"].lower()
        player_dir = f"data/{player_name}"
        if not os.path.exists(player_dir):
            os.makedirs(player_dir)

        categorical_stats_path = f"{player_dir}/categorical_stats.csv"
        if check_files and os.path.exists(categorical_stats_path):
            print(Fore.LIGHTGREEN_EX + f"{categorical_stats_path} already exists.")
        else:
            df = scrape_categorical_stats_df(player_id, player_name, page)
            if df is not None:
                print_write_message(categorical_stats_path)
                df.to_csv(categorical_stats_path, index=False)

        if check_files and glob.glob(f"{player_dir}/LL*.csv"):
            print(
                Fore.LIGHTGREEN_EX
                + f"Individual match files for {player_name} already exist."
            )
        else:
            wins_and_losses = scrape_wins_losses_and_match_urls(
                player_id, player_name, season_to_match_urls, page
            )
            write_win_loss_csvs(player_dir, wins_and_losses)


def scrape_and_write_question_categories(check_files, season_to_match_urls, page):
    seasons_dir = "data/seasons"
    if not os.path.exists(seasons_dir):
        os.makedirs(seasons_dir)

    for season in season_to_match_urls:
        season_categories_path = f"{seasons_dir}/match_categories_{season}.csv"
        if check_files and os.path.exists(season_categories_path):
            print(Fore.LIGHTGREEN_EX + f"{season_categories_path} already exists.")
        else:
            season_match_categories = scrape_season_match_categories(
                season_to_match_urls[season], page
            )
            print_write_message(season_categories_path)
            season_match_categories.to_csv(season_categories_path, index=False)


def scrape_and_write_data(players, check_files):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        login.log_into_ll(page)

        season_to_match_urls = {}
        scrape_and_write_per_player_data(
            players, check_files, season_to_match_urls, page
        )
        scrape_and_write_question_categories(check_files, season_to_match_urls, page)

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


def get_players(args):
    players = {}

    if os.path.exists(args.players_file):
        with open(args.players_file) as players_file:
            players = json.load(players_file)

    branch_player_ids = set()
    if args.branches_file and os.path.exists(args.branches_file):
        with open(args.branches_file) as branches_file:
            branches = json.load(branches_file)
            branch_player_ids.update(scrape_player_ids_from_branches(branches))

    for player_id in branch_player_ids:
        if player_id not in players:
            players[player_id] = {"name": f"Player_{player_id}"}

    return players


def get_parsed_args():
    parser = argparse.ArgumentParser(description="Scrape data from LearnedLeague.")
    parser.add_argument(
        "-s",
        "--skip_check_files",
        action="store_true",
        help="Whether to skip checking if data is already on disk (inferred from filenames) before scraping.",
    )
    parser.add_argument(
        "-p",
        "--players_file",
        type=str,
        default="friends.json",
        help="Path of JSON file containing players of interest. Defaults to friends.json",
    )
    parser.add_argument(
        "-b",
        "--branches_file",
        type=str,
        default=None,
        help="Path of JSON file containing branches of interest. Defaults to none.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_parsed_args()
    scrape_and_write_data(get_players(args), not args.skip_check_files)
