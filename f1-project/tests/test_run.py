"""Integration hors ligne : le run par defaut ne doit rien telecharger."""

from pathlib import Path

import pandas as pd
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner

from f1_project.pipeline_registry import register_pipelines


def test_default_pipeline_runs_offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = pd.DataFrame({"Driver": ["VER"], "LapNumber": [1.0]})
    schedule = pd.DataFrame(
        [
            {
                "RoundNumber": 1,
                "EventName": "Australia",
                "EventFormat": "conventional",
                "Session5": "Race",
            }
        ]
    )
    catalog = DataCatalog(
        {
            "fastf1_raw": MemoryDataset({"round_01/05_race/laps": lambda: source}),
            "fastf1_schedule": MemoryDataset(schedule),
            "params:year": MemoryDataset(2025),
        }
    )
    pipelines = register_pipelines()
    pipeline = pipelines["__default__"]
    for output in pipeline.all_outputs():
        catalog[output] = MemoryDataset()
    SequentialRunner().run(pipeline, catalog)
    assert catalog.load("fastf1_laps")["event_code"].tolist() == ["round_01"]
    assert catalog.load("fastf1_sessions")["has_laps"].tolist() == [True]
    assert not Path("data/00_cache").exists()
    assert pipeline.inputs() == {"fastf1_raw", "fastf1_schedule", "params:year"}
