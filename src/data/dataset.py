import os
import luigi
import yaml
import json

from src.data.datasets import (
    ML100kLoadAndPrepareDataset,
    ML1MLoadAndPrepareDataset,
    ML10MLoadAndPrepareDataset,
    ML20MLoadAndPrepareDataset,
    ML25MLoadAndPrepareDataset,
    YahooLoadAndPrepareDataset,
)

## Available versions of the GenerateDataset subtasks
DATASETS = dict(
    movie_lens_100k=ML100kLoadAndPrepareDataset,
    movie_lens_1m=ML1MLoadAndPrepareDataset,
    movie_lens_10m=ML10MLoadAndPrepareDataset,
    movie_lens_20m=ML20MLoadAndPrepareDataset,
    movie_lens_25m=ML25MLoadAndPrepareDataset,
    yahoo=YahooLoadAndPrepareDataset,
)

OUTPUT_PATH = os.path.join(os.getcwd(), "data/")


class DatasetGeneration(luigi.Task):
    dataset_version: str = luigi.ChoiceParameter(choices=DATASETS.keys())

    def output(self):
        return luigi.LocalTarget(
            os.path.join("data", str(self.dataset_version + "_output_path.json"))
        )

    def run(self):
        dataset = yield DATASETS[self.dataset_version](
            output_path=OUTPUT_PATH, **self.dataset_config
        )

        _output = {}
        for data in dataset:
            _output[data] = os.path.relpath(dataset[data].path)

        with open(self.output().path, "w") as file:
            json.dump(_output, file)

    @property
    def dataset_config(self):
        path = os.path.abspath(
            os.path.join("data", "{}.yaml".format(self.dataset_version))
        )

        with open(path) as f:
            dataset_config = yaml.load(f, Loader=yaml.FullLoader)

        return dataset_config
