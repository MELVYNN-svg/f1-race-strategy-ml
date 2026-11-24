"""Synthetic fixtures only: recovery and quality invariants, no sports network."""

import logging
from pathlib import Path

import pandas as pd
import pytest

from f1_project import fastf1_archive as archive
from f1_project.pit_stops import build_pit_stops
from f1_project.quality import check_table, cross_checks, telemetry_alignment


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def laps(n=3):
    return pd.DataFrame(
        {
            "DriverNumber": ["1"] * n,
            "LapNumber": list(range(1, n + 1)),
            "Time": pd.to_timedelta([90 * i for i in range(1, n + 1)], unit="s"),
            "LapTime": pd.to_timedelta([90] * n, unit="s"),
        }
    )


def schedule():
    return pd.DataFrame(
        [
            {
                "RoundNumber": 1,
                "EventFormat": "conventional",
                "EventName": "Synthetic",
                "Session5": "Race",
            }
        ]
    )


def test_truncated_but_readable_repaired_with_restorable_original(sandbox):
    path = archive.ROOT / "2024/round_01/05_race/laps.parquet"
    path.parent.mkdir(parents=True)
    laps(1).to_parquet(path, index=False)
    old_digest = archive.sha256(path)
    row = archive.record_table(path, laps(3), "laps")
    assert row["status"] == "COMPLETE"
    assert len(pd.read_parquet(path)) == 3
    assert archive.sha256(row["backup"]) == old_digest
    assert not list(path.parent.glob("*.partial"))


def test_equal_export_keeps_original_bytes_and_mtime(sandbox):
    path = archive.ROOT / "2024/x.parquet"
    archive.atomic_parquet(path, laps())
    before = (archive.sha256(path), path.stat().st_mtime_ns)
    row = archive.record_table(path, laps(), "laps")
    assert row["action"] == "verified_existing"
    assert before == (archive.sha256(path), path.stat().st_mtime_ns)


def test_source_regression_never_overwrites_larger_original(sandbox):
    path = archive.ROOT / "2024/x.parquet"
    archive.atomic_parquet(path, laps(3))
    digest = archive.sha256(path)
    assert archive.record_table(path, laps(1), "laps")["status"] == "PARTIAL"
    assert archive.sha256(path) == digest


def test_corrupt_original_is_backed_up(sandbox):
    path = archive.ROOT / "2024/x.parquet"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"synthetic corrupt file")
    row = archive.record_table(path, laps(), "laps")
    assert row["status"] == "COMPLETE"
    assert Path(row["backup"]).read_bytes() == b"synthetic corrupt file"


def test_atomic_failure_preserves_original(sandbox, monkeypatch):
    path = archive.ROOT / "2024/x.parquet"
    archive.atomic_parquet(path, laps(1))
    digest = archive.sha256(path)
    monkeypatch.setattr(
        archive.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("interrupted"))
    )
    with pytest.raises(OSError):
        archive.atomic_parquet(path, laps(3))
    assert archive.sha256(path) == digest
    assert not list(path.parent.glob("*.partial"))


def test_legacy_presence_never_means_complete(sandbox):
    path = archive.ROOT / "2024/round_01/05_race/laps.parquet"
    archive.atomic_parquet(path, laps(1))
    coverage, _ = archive.audit(schedule(), 2024)
    assert coverage.loc[coverage.dataset.eq("laps"), "status"].item() == "PARTIAL"
    assert "MISSING" in set(coverage.status)


def test_checkpoint_detects_tampering(sandbox):
    path = archive.ROOT / "2024/x.parquet"
    row = archive.record_table(path, laps(), "laps")
    records = [
        dict(row, dataset=name)
        for name in (*archive.SESSION_TABLES, "car_data", "position")
    ]
    manifest = {
        "version": archive.VERSION,
        "fastf1_version": archive.fastf1.__version__,
        "records": records,
    }
    assert archive.verified_manifest(manifest)
    laps(1).to_parquet(path)
    assert not archive.verified_manifest(manifest)


def test_retry_is_bounded_and_rate_limit_not_hammered():
    calls, sleeps = [], []

    def fail():
        calls.append(1)
        raise ConnectionError("synthetic")

    with pytest.raises(ConnectionError):
        archive.retry_call(fail, sleep=sleeps.append)
    assert len(calls) == 3
    assert sleeps == [2, 4]

    class RateLimitExceededError(Exception):
        pass

    calls.clear()

    def rate():
        calls.append(1)
        raise RateLimitExceededError()

    with pytest.raises(RateLimitExceededError):
        archive.retry_call(rate, sleep=sleeps.append)
    assert len(calls) == 1


def test_empty_source_and_empty_derived_are_distinct(sandbox):
    path = archive.ROOT / "2024/x.parquet"
    assert (
        archive.record_table(path, pd.DataFrame(), "weather")["status"]
        == "SOURCE_UNAVAILABLE"
    )
    assert (
        archive.record_table(
            path, pd.DataFrame(), "pit_stops", empty_status="NOT_APPLICABLE"
        )["status"]
        == "NOT_APPLICABLE"
    )
    assert archive.record_table(path, None, "laps")["status"] == "ERROR"


def test_retirement_and_dns_not_treated_as_winner_lap_deficit():
    result = pd.DataFrame({"DriverNumber": ["1", "2"], "Laps": [3, 0]})
    assert cross_checks(laps(3), result, "Race") == []
    assert cross_checks(laps(1), result, "Race")[0]["code"] == "laps_below_classified"


def test_quality_retains_unusual_laps_and_flags_negative_duration():
    frame = laps(2)
    frame.loc[0, "LapTime"] = pd.Timedelta(seconds=-1)
    frame.loc[1, "LapTime"] = pd.Timedelta(hours=1)
    original = frame.copy()
    issues, _ = check_table(frame, "laps")
    assert any(i["code"] == "negative_duration" for i in issues)
    pd.testing.assert_frame_equal(frame, original)


def test_pairing_same_lap_and_unmatched_events():
    frame = pd.DataFrame(
        {
            "DriverNumber": ["1"] * 3,
            "LapNumber": [1, 2, 3],
            "PitInTime": pd.to_timedelta([None, 100, 200], unit="s"),
            "PitOutTime": pd.to_timedelta([10, 130, None], unit="s"),
            "Compound": ["SOFT", "MEDIUM", "HARD"],
        }
    )
    result = build_pit_stops(
        frame, pd.DataFrame({"Time": pd.to_timedelta([0], unit="s"), "Status": ["1"]})
    )
    assert result.pair_status.tolist() == ["UNMATCHED_OUT", "PAIRED", "UNMATCHED_IN"]
    assert result.loc[1, "lane_elapsed"] == pd.Timedelta(seconds=30)
    assert result.loc[1, "context"] == "GREEN"
    assert result.is_estimated.all()


def test_alignment_measures_real_offsets():
    a = pd.DataFrame(
        {"Date": pd.to_datetime(["2024-01-01T00:00:00.000", "2024-01-01T00:00:00.500"])}
    )
    b = pd.DataFrame(
        {"Date": pd.to_datetime(["2024-01-01T00:00:00.100", "2024-01-01T00:00:00.600"])}
    )
    assert telemetry_alignment(a, b)["nearest_p50_s"] == pytest.approx(0.1)


def test_pit_events_only_exits_have_timedelta_nat():
    frame = pd.DataFrame(
        {
            "DriverNumber": ["1"],
            "LapNumber": [1],
            "PitInTime": pd.to_timedelta([None]),
            "PitOutTime": pd.to_timedelta([10], unit="s"),
        }
    )
    output = build_pit_stops(frame)
    assert output.pair_status.item() == "UNMATCHED_OUT"
    assert str(output.lane_elapsed.dtype) == "timedelta64[ns]"


def test_windows_transient_replace_is_retried(sandbox, monkeypatch):
    source, dest = Path("source"), Path("dest")
    source.write_text("new")
    replace = archive.os.replace
    calls = []

    def transient(a, b):
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError("temporary reader")
        replace(a, b)

    monkeypatch.setattr(archive.os, "replace", transient)
    monkeypatch.setattr(archive.time, "sleep", lambda _: None)
    archive.replace_file(source, dest)
    assert dest.read_text() == "new"


def test_throttle_104_is_availability_sentinel_and_not_physical_outlier():
    frame = pd.DataFrame({"Throttle": [104, 101, 100]})
    issues, _ = check_table(frame, "car_data")
    assert (
        next(i for i in issues if i["code"] == "source_unavailable_value")["count"] == 1
    )
    assert next(i for i in issues if i["code"] == "channel_outlier")["count"] == 1


def test_event_comparison_normalizes_dates_without_changing_source(sandbox):
    source = schedule()
    source["Session5Date"] = ["2024-01-01 15:00:00+01:00"]
    frame = source.copy()
    frame["Session5Date"] = pd.to_datetime(frame.Session5Date)
    path = archive.ROOT / "2024/round_01/event.parquet"
    archive.atomic_parquet(path, frame)
    digest = archive.sha256(path)
    assert archive.event_inventory(source, 2024).status.item() == "COMPLETE"
    assert archive.sha256(path) == digest


def test_driver_inventory_dns_preserves_session_local_identity(sandbox):
    folder = archive.ROOT / "2024/round_01/05_race"
    archive.atomic_parquet(folder / "laps.parquet", laps(3))
    result = pd.DataFrame(
        {
            "DriverNumber": ["1", "2"],
            "TeamName": ["Team A", "Team B"],
            "Status": ["Finished", "Did not start"],
        }
    )
    archive.atomic_parquet(folder / "results.parquet", result)
    coverage, _ = archive.audit(schedule(), 2024)
    drivers = archive.driver_inventory(schedule(), 2024, coverage)
    dns = drivers.loc[drivers.driver.eq("2")]
    assert set(dns.loc[dns.dataset.ne("results"), "status"]) == {"NOT_APPLICABLE"}
    assert set(dns.team) == {"Team B"}


def test_local_preparation_uses_existing_tables_and_never_loads_telemetry(
    sandbox, monkeypatch
):
    folder = archive.ROOT / "2024/round_01/05_race"
    archive.atomic_parquet(folder / "laps.parquet", laps(3))
    # A corrupt telemetry fixture must remain lazy during preparation.
    (folder / "car_data").mkdir()
    (folder / "car_data/1.parquet").write_bytes(b"not read by preparation")
    archive.prepare_local(schedule(), 2024)
    table = pd.read_parquet("data/03_primary/fastf1/2024/laps.parquet")
    assert len(table) == 3
    assert set(table.year) == {2024}


def test_source_soft_exceptions_are_captured_without_exposing_credentials():
    handler = archive.SourceDiagnostics()
    error = RuntimeError("source unavailable")
    record = logging.LogRecord(
        "fastf1.core",
        logging.DEBUG,
        "",
        0,
        "timing data",
        (),
        (RuntimeError, error, None),
    )
    handler.emit(record)
    assert handler.errors == [
        {
            "operation": "timing data",
            "type": "RuntimeError",
            "message": "source unavailable",
        }
    ]


def test_missing_laps_with_local_results_are_not_called_source_unavailable(sandbox):
    folder = archive.ROOT / "2024/round_01/05_race"
    archive.atomic_parquet(
        folder / "results.parquet",
        pd.DataFrame({"DriverNumber": ["1"], "Status": ["Finished"]}),
    )
    coverage, _ = archive.audit(schedule(), 2024)
    result = archive.driver_inventory(schedule(), 2024, coverage)
    assert result.loc[result.dataset.eq("laps"), "status"].item() == "MISSING"


def test_sprint_and_testing_follow_calendar():
    data = pd.DataFrame(
        [
            {
                "RoundNumber": 0,
                "EventFormat": "testing",
                "EventName": "Test",
                "Session1": "Practice 1",
                "Session4": "None",
            },
            {
                "RoundNumber": 2,
                "EventFormat": "sprint_qualifying",
                "EventName": "Sprint",
                "Session2": "Sprint Qualifying",
                "Session3": "Sprint",
            },
        ]
    )
    records = list(archive.expected_sessions(data, 2024))
    assert [r["session_code"] for r in records] == [
        "01_practice_1",
        "02_sprint_qualifying",
        "03_sprint",
    ]
    assert records[0]["testing_number"] == 1
