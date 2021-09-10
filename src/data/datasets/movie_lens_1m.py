import os
import luigi
import pickle
import pandas as pd
import numpy as np
import random

from ..utils import DownloadDataset


class ML1MLoadAndPrepareDataset(luigi.Task):
    output_path: str = luigi.Parameter(default=os.path.join(os.getcwd(), "data/"))
    n_groups: int = luigi.Parameter(default=4)

    def __init__(self, *args, **kwargs):
        super(ML1MLoadAndPrepareDataset, self).__init__(*args, **kwargs)

        self.data_dir = os.path.join(self.output_path, "ml-1m")

    def requires(self):
        return DownloadDataset(dataset="ml-1m", output_path=self.output_path)

    def output(self):
        return {
            "train_users_dict": luigi.LocalTarget(
                os.path.join(self.data_dir, "train_users_dict.pkl")
            ),
            "train_users_history_lens": luigi.LocalTarget(
                os.path.join(self.data_dir, "train_users_history_lens.pkl")
            ),
            "eval_users_dict": luigi.LocalTarget(
                os.path.join(self.data_dir, "eval_users_dict.pkl")
            ),
            "eval_users_history_lens": luigi.LocalTarget(
                os.path.join(self.data_dir, "eval_users_history_lens.pkl")
            ),
            "users_history_lens": luigi.LocalTarget(
                os.path.join(self.data_dir, "users_history_lens.pkl")
            ),
            "movies_id_to_movies": luigi.LocalTarget(
                os.path.join(self.data_dir, "movies_id_to_movies.pkl")
            ),
            "movies_groups": luigi.LocalTarget(
                os.path.join(self.data_dir, "movies_groups.pkl")
            ),
        }

    def run(self):
        datasets = self.load_dataset()
        self.prepareDataset(datasets)

    def load_dataset(self):

        ratings_list = [
            i.strip().split("::")
            for i in open(os.path.join(self.data_dir, "ratings.dat"), "r").readlines()
        ]
        users_list = [
            i.strip().split("::")
            for i in open(os.path.join(self.data_dir, "users.dat"), "r").readlines()
        ]
        movies_list = [
            i.strip().split("::")
            for i in open(
                os.path.join(self.data_dir, "movies.dat"), encoding="latin-1"
            ).readlines()
        ]

        ratings_df = pd.DataFrame(
            ratings_list,
            columns=["user_id", "movie_id", "rating", "timestamp"],
            dtype=np.uint32,
        )

        movies_df = pd.DataFrame(movies_list, columns=["movie_id", "title", "genres"])
        movies_df["movie_id"] = movies_df["movie_id"].apply(pd.to_numeric)

        users_df = pd.DataFrame(
            users_list, columns=["user_id", "gender", "age", "occupation", "zip_code"]
        )

        datasets = {"ratings": ratings_df, "movies": movies_df, "users": users_df}
        for dataset in datasets:
            datasets[dataset].to_csv(
                os.path.join(self.data_dir, str(dataset + ".csv")),
                index=False,
            )

        return datasets

    def prepareDataset(self, datasets):

        movies_id_to_movies = {
            row[0]: row[1:] for index, row in datasets["movies"].iterrows()
        }
        movies_groups = {
            row[0]: random.randint(1, self.n_groups)
            for index, row in datasets["movies"].iterrows()
        }
        datasets["ratings"] = datasets["ratings"].applymap(int)

        users_dict = {user: [] for user in set(datasets["ratings"]["user_id"])}

        ratings_df_gen = datasets["ratings"].iterrows()
        users_dict_for_history_len = {
            user: [] for user in set(datasets["ratings"]["user_id"])
        }
        for data in ratings_df_gen:
            users_dict[data[1]["user_id"]].append(
                (data[1]["movie_id"], data[1]["rating"])
            )
            if data[1]["rating"] >= 4:
                users_dict_for_history_len[data[1]["user_id"]].append(
                    (data[1]["movie_id"], data[1]["rating"])
                )
        users_history_lens = [
            len(users_dict_for_history_len[u])
            for u in set(datasets["ratings"]["user_id"])
        ]

        users_num = max(datasets["ratings"]["user_id"]) + 1
        items_num = max(datasets["ratings"]["movie_id"]) + 1

        # 6041 3953
        # print(users_num, items_num)

        # Training setting
        train_users_num = int(users_num * 0.8)
        train_items_num = items_num
        train_users_dict = {k: users_dict.get(k) for k in range(1, train_users_num + 1)}
        train_users_history_lens = users_history_lens[:train_users_num]

        # Evaluating setting
        eval_users_num = int(users_num * 0.2)
        eval_items_num = items_num
        eval_users_dict = {
            k: users_dict[k] for k in range(users_num - eval_users_num, users_num)
        }
        eval_users_history_lens = users_history_lens[-eval_users_num:]

        with open(self.output()["train_users_dict"].path, "wb") as file:
            pickle.dump(train_users_dict, file)

        with open(self.output()["train_users_history_lens"].path, "wb") as file:
            pickle.dump(train_users_history_lens, file)

        with open(self.output()["eval_users_dict"].path, "wb") as file:
            pickle.dump(eval_users_dict, file)

        with open(self.output()["eval_users_history_lens"].path, "wb") as file:
            pickle.dump(eval_users_history_lens, file)

        with open(self.output()["users_history_lens"].path, "wb") as file:
            pickle.dump(users_history_lens, file)

        with open(self.output()["movies_id_to_movies"].path, "wb") as file:
            pickle.dump(movies_id_to_movies, file)

        with open(self.output()["movies_groups"].path, "wb") as file:
            pickle.dump(movies_groups, file)
