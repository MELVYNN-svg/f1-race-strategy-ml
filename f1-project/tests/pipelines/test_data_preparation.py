"""Selection des partitions, contexte et couverture des sessions."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from f1_project.pipelines.data_preparation.nodes import (
    build_inventory,
    build_sessions,
    concatenate_tables,
    normalize_table,
    partition_metadata,
)


def must_not_load():
    raise AssertionError(
        "La telemetrie et les tables hors sujet doivent rester paresseuses"
    )


def test_concatenation_preserves_source_types_and_session_context():
    source = pd.DataFrame(
        {
            "Driver": ["VER"],
            "LapTime": pd.to_timedelta([90], unit="s"),
        }
    )
    partitions = {
        "round_02/03_sprint/laps": lambda: source,
        "round_01/05_race/laps": lambda: source,
        "test_01/01_practice_1/laps": lambda: source,
        "round_01/05_race/car_data/1": must_not_load,
        "round_01/05_race/position/1": must_not_load,
        "schedule": must_not_load,
    }
    original = source.copy(deep=True)
    result = concatenate_tables(partitions, 2025)
    laps = result["fastf1_laps"]
    assert laps["event_code"].tolist() == ["round_01", "round_02", "test_01"]
    assert laps["session_name"].tolist() == ["race", "sprint", "practice_1"]
    assert laps["round_number"].tolist() == [1, 2, 0]
    assert laps["year"].tolist() == [2025] * 3
    assert laps["LapTime"].dt.total_seconds().tolist() == [90] * 3
    assert result["fastf1_results"].empty
    assert_frame_equal(source, original)


def test_inventory_never_loads_data_and_records_driver_number():
    inventory = build_inventory(
        {
            "round_01/05_race/car_data/1": must_not_load,
            "round_01/05_race/laps": must_not_load,
            "round_01/event": must_not_load,
            "schedule": must_not_load,
        },
        2025,
    )
    assert len(inventory) == 3  # noqa: PLR2004
    assert (
        inventory.loc[inventory["table"].eq("car_data"), "driver_number"].item() == "1"
    )


def test_sessions_includes_missing_races_and_uses_sprint_folder_order():
    partitions = {"round_02/03_sprint/laps": must_not_load}
    schedule = pd.DataFrame(
        [
            {
                "RoundNumber": 0,
                "EventName": "Testing",
                "EventFormat": "testing",
                "Session1": "Practice 1",
            },
            {
                "RoundNumber": 2,
                "EventName": "China",
                "EventFormat": "sprint_qualifying",
                "Session3": "Sprint",
                "Session5": "Race",
            },
        ]
    )
    sessions = build_sessions(build_inventory(partitions, 2025), schedule)
    assert sessions["event_code"].tolist() == ["test_01", "round_02", "round_02"]
    assert sessions["has_laps"].tolist() == [False, True, False]
    assert sessions["file_count"].tolist() == [0, 1, 0]
    assert not sessions["has_results"].any()


@pytest.mark.parametrize(
    "partition", ["schedule", "notes/readme", "round_01/notes", "round_01/x/y/z"]
)
def test_ignore_non_session_paths(partition):
    assert partition_metadata(partition, 2025) is None


def test_empty_inventory_still_reports_expected_sessions():
    inventory = build_inventory({}, 2025)
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
    assert not build_sessions(inventory, schedule)["has_laps"].any()


def test_testing_placeholder_sessions_are_not_counted():
    schedule = pd.DataFrame(
        [
            {
                "RoundNumber": 0,
                "EventName": "Testing",
                "EventFormat": "testing",
                "Session1": "Practice 1",
                "Session4": "None",
                "Session5": "None",
            }
        ]
    )
    sessions = build_sessions(build_inventory({}, 2025), schedule)
    assert sessions["session_code"].tolist() == ["01_practice_1"]


def test_mixed_boolean_exports_can_be_saved_to_parquet(tmp_path):
    tables = concatenate_tables(
        {
            "round_01/05_race/laps": lambda: pd.DataFrame(
                {"IsPersonalBest": [True, False]}
            ),
            "round_02/05_race/laps": lambda: pd.DataFrame(
                {"IsPersonalBest": ["True", "False", pd.NA]}
            ),
        },
        2025,
    )
    laps = tables["fastf1_laps"]
    path = tmp_path / "laps.parquet"
    laps.to_parquet(path)
    assert str(pd.read_parquet(path)["IsPersonalBest"].dtype) == "boolean"
    assert laps["IsPersonalBest"].dropna().tolist() == [True, False, True, False]


def test_unknown_boolean_value_is_not_silently_erased():
    with pytest.raises(ValueError, match="IsPersonalBest"):
        normalize_table(pd.DataFrame({"IsPersonalBest": ["unexpected"]}), "laps")


def test_race_control_numbers_and_event_dates_are_normalized():
    numbers = normalize_table(
        pd.DataFrame({"Lap": ["1", None], "Sector": [2.0, None]}), "race_control"
    )
    assert str(numbers["Lap"].dtype) == "Int64"
    assert str(numbers["Sector"].dtype) == "Int64"
    dates = normalize_table(
        pd.DataFrame({"Session1Date": pd.to_datetime(["2025-03-14T12:00:00+11:00"])}),
        "event",
    )
    assert dates["Session1Date"].item() == pd.Timestamp("2025-03-14T01:00:00Z")
