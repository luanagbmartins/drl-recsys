import os
import luigi
import pickle
import pandas as pd
import numpy as np
import random
from sklearn import preprocessing
from sentence_transformers import SentenceTransformer
from math import ceil

from ..utils import DownloadDataset
from ..utils import split_train_test


class ML100kLoadAndPrepareDataset(luigi.Task):
    output_path: str = luigi.Parameter(default=os.path.join(os.getcwd(), "data/"))
    n_groups: int = luigi.IntParameter(default=4)

    def __init__(self, *args, **kwargs):
        super(ML100kLoadAndPrepareDataset, self).__init__(*args, **kwargs)

        self.data_dir = os.path.join(self.output_path, "ml-100k")

    def requires(self):
        return DownloadDataset(dataset="ml-100k", output_path=self.output_path)

    def output(self):
        return {
            "items_df": luigi.LocalTarget(os.path.join(self.data_dir, "movies.csv")),
            "items_metadata": luigi.LocalTarget(
                os.path.join(self.data_dir, "items_metadata.csv")
            ),
            "title_emb": luigi.LocalTarget(
                os.path.join(self.data_dir, "title_emb.csv")
            ),
            "users_df": luigi.LocalTarget(os.path.join(self.data_dir, "users.csv")),
            "ratings_df": luigi.LocalTarget(os.path.join(self.data_dir, "ratings.csv")),
            "train_users_dict": luigi.LocalTarget(
                os.path.join(self.data_dir, "train_users_dict.pkl")
            ),
            "eval_users_dict": luigi.LocalTarget(
                os.path.join(self.data_dir, "eval_users_dict.pkl")
            ),
            "train_users_df": luigi.LocalTarget(
                os.path.join(self.data_dir, "train_users_df.csv")
            ),
            "eval_users_df": luigi.LocalTarget(
                os.path.join(self.data_dir, "eval_users_df.csv")
            ),
            "users_history_lens": luigi.LocalTarget(
                os.path.join(self.data_dir, "users_history_lens.pkl")
            ),
            "item_groups": luigi.LocalTarget(
                os.path.join(self.data_dir, "item_groups.pkl")
            ),
        }

    def run(self):
        print("---------- Load Dataset")
        datasets = self.load_dataset()

        print("---------- Prepare Dataset")
        self.prepareDataset(datasets)

    def load_dataset(self):
        ratings_df = pd.read_csv(
            os.path.join(self.data_dir, "u.data"),
            sep="\t",
            names=["user_id", "item_id", "rating", "timestamp"],
            engine="python",
            dtype=np.uint32,
        )
        users_df = pd.read_csv(
            os.path.join(self.data_dir, "u.user"),
            sep="|",
            names=["user_id", "age", "gender", "occupation", "zip_code"],
            engine="python",
        )
        movies_list = [
            i.strip().split("|")
            for i in open(
                os.path.join(self.data_dir, "u.item"), encoding="latin-1"
            ).readlines()
        ]
        movies_df = pd.DataFrame(
            movies_list,
            columns=[
                "item_id",
                "item_name",
                "release_date",
                "video_release_date",
                "imdb_url",
                "unknown",
                "Action",
                "Adventure",
                "Animation",
                "Childrens",
                "Comedy",
                "Crime",
                "Documentary",
                "Drama",
                "Fantasy",
                "Film_Noir",
                "Horror",
                "Musical",
                "Mystery",
                "Romance",
                "Sci-Fi",
                "Thriller",
                "War",
                "Western",
            ],
        )
        movies_df["item_id"] = movies_df["item_id"].apply(pd.to_numeric)

        # Encode target labels with value between 0 and n_classes-1
        movies_encoder = preprocessing.LabelEncoder()
        movies_encoder.fit(movies_df["item_id"].values)
        movies_df["item_id"] = movies_encoder.transform(movies_df["item_id"].values)
        ratings_df["item_id"] = movies_encoder.transform(ratings_df["item_id"].values)

        users_encoder = preprocessing.LabelEncoder()
        users_encoder.fit(users_df["user_id"].values)
        users_df["user_id"] = users_encoder.transform(users_df["user_id"].values)
        ratings_df["user_id"] = users_encoder.transform(ratings_df["user_id"].values)

        items_metadata = movies_df.drop(
            columns=[
                "item_name",
                "release_date",
                "video_release_date",
                "imdb_url",
            ]
        )

        filter_col = items_metadata.columns[1:]
        items_metadata["metadata"] = items_metadata[filter_col].values.tolist()

        movies_df = movies_df[["item_id", "item_name", "release_date"]]

        bert = SentenceTransformer("all-MiniLM-L12-v1")
        title_emb = bert.encode(movies_df["item_name"].tolist())
        title_emb = pd.DataFrame(title_emb.tolist())

        # Save preprocessed dataframes
        datasets = {
            "ratings": ratings_df,
            "movies": movies_df,
            "users": users_df,
            "items_metadata": items_metadata,
            "title_emb": title_emb,
        }
        for dataset in datasets:
            datasets[dataset].to_csv(
                os.path.join(self.data_dir, str(dataset + ".csv")),
                index=False,
            )

        return datasets

    def prepareDataset(self, datasets):

        datasets["ratings"] = datasets["ratings"].sort_values("timestamp")
        datasets["ratings"] = datasets["ratings"].applymap(int)

        users_dict = {user: [] for user in set(datasets["ratings"]["user_id"])}

        ratings_df_gen = datasets["ratings"].iterrows()
        users_dict_positive_items = {
            user: [] for user in set(datasets["ratings"]["user_id"])
        }
        for data in ratings_df_gen:
            users_dict[data[1]["user_id"]].append(
                (data[1]["item_id"], data[1]["rating"])
            )
            if data[1]["rating"] >= 4:
                users_dict_positive_items[data[1]["user_id"]].append(
                    (data[1]["item_id"], data[1]["rating"])
                )
        users_history_lens = [
            len(users_dict_positive_items[u])
            for u in set(datasets["ratings"]["user_id"])
        ]

        users_num = max(datasets["ratings"]["user_id"]) + 1
        items_num = max(datasets["ratings"]["item_id"]) + 1

        print(users_num, items_num)

        # items groups
        z = np.random.geometric(p=0.35, size=items_num)
        w = z % self.n_groups
        w = [i if i > 0 else self.n_groups for i in w]
        item_groups = {i: w[i] for i in range(items_num)}

        train_df, test_df = split_train_test(datasets["ratings"])
        train_df.to_csv(self.output()["train_users_df"].path)
        test_df.to_csv(self.output()["eval_users_df"].path)
        print(train_df.shape, test_df.shape)

        # Training setting
        train_users_dict = {user: [] for user in set(train_df["user_id"])}
        ratings_df_gen = train_df.iterrows()
        for data in ratings_df_gen:
            train_users_dict[data[1]["user_id"]].append(
                (data[1]["item_id"], data[1]["rating"])
            )

        # Evaluating setting
        eval_users_dict = {user: [] for user in set(test_df["user_id"])}
        ratings_df_gen = test_df.iterrows()
        for data in ratings_df_gen:
            eval_users_dict[data[1]["user_id"]].append(
                (data[1]["item_id"], data[1]["rating"])
            )

        # Save processed data
        with open(self.output()["train_users_dict"].path, "wb") as file:
            pickle.dump(train_users_dict, file)

        with open(self.output()["eval_users_dict"].path, "wb") as file:
            pickle.dump(eval_users_dict, file)

        with open(self.output()["users_history_lens"].path, "wb") as file:
            pickle.dump(users_history_lens, file)

        with open(self.output()["item_groups"].path, "wb") as file:
            pickle.dump(item_groups, file)
