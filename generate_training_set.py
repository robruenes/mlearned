import os
import pandas as pd
from colorama import Fore


def get_player_to_files(path):
    player_to_files = {}
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            player = full_path.split("/", 2)[1]

            # Skip dirs and files that may be byproducts of
            # running this script more than once.
            if player == "aggregated" or player == "training_set.csv":
                continue

            if player not in player_to_files:
                player_to_files[player] = []

            player_to_files[player].append(full_path)

    return player_to_files


def write_per_player_aggregated_csvs(player_to_files, data_path, agg_path):
    for player in player_to_files.keys():
        player_data_path = f"{data_path}/{player}"
        print(
            Fore.LIGHTYELLOW_EX
            + f"...Reading data for {player} from {player_data_path}"
        )

        df = pd.DataFrame()
        for file in player_to_files[player]:
            match_df = pd.read_csv(file, sep="\t", encoding="utf-8")
            if "match_stats" in file:
                df = pd.concat([df, match_df], ignore_index=True)

        # Broadcast the career stats.
        career_stats = pd.read_csv(
            f"{player_data_path}/career_stats.csv", sep="\t", encoding="utf-8"
        )

        # TODO: There's gotta be a better way to do this
        for col in career_stats.columns:
            df[col] = career_stats[col].values[0]

        # Broadcast categorical performance.
        categorical_performance = pd.read_csv(
            f"{player_data_path}/latest_league_stats.csv", sep="\t", encoding="utf-8"
        )
        categorical_performance = categorical_performance.filter(
            ["Category", "Percent Correct"]
        )

        categorical_performance["Category"] = categorical_performance[
            "Category"
        ].replace(
            {
                0: "AMER HIST Pct Correct",
                1: "ART Pct Correct",
                2: "BUS/ECON Pct Correct",
                3: "CLASS MUSIC Pct Correct",
                4: "CURR EVENTS Pct Correct",
                5: "FILM Pct Correct",
                6: "FOOD/DRINK Pct Correct",
                7: "GAMES/SPORT Pct Correct",
                8: "GEOGRAPHY Pct Correct",
                9: "LANGUAGE Pct Correct",
                10: "LIFESTYLE Pct Correct",
                11: "LITERATURE Pct Correct",
                12: "MATH Pct Correct",
                13: "POP MUSIC Pct Correct",
                14: "SCIENCE Pct Correct",
                15: "TELEVISION Pct Correct",
                16: "THEATRE Pct Correct",
                17: "WORLD HIST Pct Correct",
            }
        )

        categorical_performance = categorical_performance.T.reset_index(drop=True)
        categorical_performance.columns = categorical_performance.iloc[0]
        categorical_performance = categorical_performance.iloc[1:, :]

        # TODO: There's gotta be a better way to do this
        for col in categorical_performance.columns:
            df[col] = categorical_performance[col].values[0]

        if not os.path.exists(agg_path):
            os.makedirs(agg_path)

        player_agg_path = f"{agg_path}/{player}.csv"
        print(Fore.LIGHTYELLOW_EX + f"...wrote intermediate file at {player_agg_path}")
        df.to_csv(f"{player_agg_path}", sep="\t", encoding="utf-8", index=False)


def write_training_set(data_path, agg_path):
    training_set = pd.DataFrame()
    print(Fore.LIGHTYELLOW_EX + f"...combining intermediate files")
    for root, _, files in os.walk(agg_path):
        for file in files:
            agg_player_stats = os.path.join(root, file)
            agg_player_stats_df = pd.read_csv(
                agg_player_stats, sep="\t", encoding="utf-8"
            )
            training_set = pd.concat(
                [training_set, agg_player_stats_df], ignore_index=True
            )
    training_set_path = f"{data_path}/training_set.csv"

    # Before writing the training set, drop any entry where the player
    # forfeited.
    training_set = training_set[training_set["Result"] != -1]

    training_set.to_csv(training_set_path, sep="\t", encoding="utf-8", index=False)
    print(Fore.LIGHTGREEN_EX + f"Wrote training set to {training_set_path}!")


def generate_training_set():
    print(Fore.LIGHTCYAN_EX + "Building training set...")
    data_path = "data"
    player_to_files = get_player_to_files(data_path)
    agg_path = f"{data_path}/aggregated"
    write_per_player_aggregated_csvs(player_to_files, data_path, agg_path)
    write_training_set(data_path, agg_path)


if __name__ == "__main__":
    generate_training_set()
