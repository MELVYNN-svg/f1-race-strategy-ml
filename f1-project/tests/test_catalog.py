"""Valide les chemins du catalogue sans exiger les donnees locales."""

from pathlib import Path

import pandas as pd
import pytest
from kedro.config import OmegaConfigLoader
from kedro.io import DataCatalog

PROJECT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("runtime_params,year", [({}, 2025), ({"year": 2024}, 2024)])
def test_catalog_year_is_consistent_for_parameters_and_paths(runtime_params, year):
    config = OmegaConfigLoader(
        conf_source=str(PROJECT / "conf"),
        base_env="base",
        default_run_env="local",
        runtime_params=runtime_params,
    )
    assert int(config["parameters"]["year"]) == year
    for dataset in config["catalog"].values():
        path = dataset.get("filepath", dataset.get("path"))
        assert str(year) in path


def test_factory_reads_only_the_requested_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = OmegaConfigLoader(
        conf_source=str(PROJECT / "conf"),
        base_env="base",
        default_run_env="local",
    )
    examples = {
        "fastf1_table__round_02__03_sprint__laps": "fastf1/2025/round_02/03_sprint/laps.parquet",
        "fastf1_driver__round_01__05_race__car_data__1": "fastf1/2025/round_01/05_race/car_data/1.parquet",
        "fastf1_driver__round_01__05_race__position__1": "fastf1/2025/round_01/05_race/position/1.parquet",
        "openf1_table__9683__laps": "openf1/2025/9683/laps.parquet",
    }
    for relative in examples.values():
        path = tmp_path / "data/01_raw" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"value": [42]}).to_parquet(path)
    catalog = DataCatalog.from_config(config["catalog"])
    for name in examples:
        assert catalog.load(name)["value"].tolist() == [42]
    partitions = catalog.load("fastf1_raw")
    assert set(partitions) == {
        "round_02/03_sprint/laps",
        "round_01/05_race/car_data/1",
        "round_01/05_race/position/1",
    }
