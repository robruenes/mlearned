import os
import pandas as pd
from colorama import Fore


def get_friend_to_files(path):
    friend_to_files = {}
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            friend = full_path.split("/", 2)[1]

            # Skip dirs and files that may be byproducts of
            # running this script more than once.
            if friend == "aggregated" or friend == "training_set.csv":
                continue

            if friend not in friend_to_files:
                friend_to_files[friend] = []

            friend_to_files[friend].append(full_path)

    return friend_to_files


def write_per_friend_aggregated_csvs(friend_to_files, data_path, agg_path):
    for friend in friend_to_files.keys():
        friend_data_path = f"{data_path}/{friend}"
        print(
            Fore.LIGHTYELLOW_EX
            + f"...Reading data for {friend} from {friend_data_path}"
        )

        df = pd.DataFrame()
        for file in friend_to_files[friend]:
            match_df = pd.read_csv(file, sep="\t", encoding="utf-8")
            if "match_stats" in file:
                df = pd.concat([df, match_df], ignore_index=True)

        # Broadcast the career stats.
        career_stats = pd.read_csv(
            f"{friend_data_path}/career_stats.csv", sep="\t", encoding="utf-8"
        )
        for col in career_stats.columns:
            df[col] = career_stats[col].values[0]

        if not os.path.exists(agg_path):
            os.makedirs(agg_path)

        friend_agg_path = f"{agg_path}/{friend}.csv"
        print(Fore.LIGHTYELLOW_EX + f"...wrote intermediate file at {friend_agg_path}")
        df.to_csv(f"{friend_agg_path}", sep="\t", encoding="utf-8", index=False)


def write_training_set(data_path, agg_path):
    training_set = pd.DataFrame()
    print(Fore.LIGHTYELLOW_EX + f"...combining intermediate files")
    for root, _, files in os.walk(agg_path):
        for file in files:
            agg_friend_stats = os.path.join(root, file)
            agg_friend_stats_df = pd.read_csv(
                agg_friend_stats, sep="\t", encoding="utf-8"
            )
            training_set = pd.concat(
                [training_set, agg_friend_stats_df], ignore_index=True
            )
    training_set_path = f"{data_path}/training_set.csv"
    training_set.to_csv(training_set_path, sep="\t", encoding="utf-8")
    print(Fore.LIGHTGREEN_EX + f"Wrote training set to {training_set_path}!")


def generate_training_set():
    print(Fore.LIGHTCYAN_EX + "Building training set...")
    data_path = "data"
    friend_to_files = get_friend_to_files(data_path)
    agg_path = f"{data_path}/aggregated"
    write_per_friend_aggregated_csvs(friend_to_files, data_path, agg_path)
    write_training_set(data_path, agg_path)


if __name__ == "__main__":
    generate_training_set()
