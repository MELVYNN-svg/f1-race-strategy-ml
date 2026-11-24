import json
import re
from datetime import datetime, timezone
from pathlib import Path

import fastf1
import pandas as pd

ROOT = Path("data/01_raw/fastf1")
CACHE = Path("data/00_cache/fastf1")

COLUMNS = [
    "year",
    "event",
    "round",
    "session",
    "dataset",
    "driver",
    "status",
    "rows",
    "path",
    "message",
    "utc",
]


def configure_cache():
    CACHE.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.configure(cache_dir=str(CACHE))


def get_schedule(year):
    configure_cache()

    schedule = fastf1.get_event_schedule(
        int(year),
        include_testing=True,
    )

    if schedule.empty:
        raise ValueError(f"Aucun événement trouvé pour {year}")

    return pd.DataFrame(schedule).reset_index(drop=True)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def prepare(data):
    df = pd.DataFrame(data).reset_index(drop=True).copy()

    for col in df.select_dtypes(include=["object"]).columns:

        def convert(value):
            if isinstance(value, (dict, list, tuple)):
                return json.dumps(
                    value,
                    ensure_ascii=False,
                    default=str,
                )

            if value is None or value is pd.NA:
                return None

            try:
                if pd.isna(value):
                    return None
            except (TypeError, ValueError):
                pass

            return str(value)

        df[col] = df[col].map(convert).astype("string")

    return df


def valid_parquet(path):
    if not path.is_file():
        return False

    try:
        frame = pd.read_parquet(path)
        return not frame.empty
    except Exception:
        return False


def log_event(
    report,
    log_path,
    meta,
    dataset,
    status,
    driver="",
    rows=None,
    path="",
    message="",
):
    entry = {
        **meta,
        "dataset": dataset,
        "driver": str(driver),
        "status": status,
        "rows": rows,
        "path": str(path),
        "message": str(message),
        "utc": datetime.now(timezone.utc).isoformat(),
    }

    report.append(entry)

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with log_path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(
                entry,
                ensure_ascii=False,
                default=str,
            )
            + "\n"
        )

    print(
        f"[{status}] {dataset}"
        + (f" | Driver {driver}" if driver else "")
        + (f" | {rows} lignes" if rows is not None else "")
        + (f" | {message}" if message else ""),
        flush=True,
    )


def save_table(
    path,
    loader,
    report,
    log_path,
    meta,
    name,
    driver="",
):
    from f1_project.fastf1_archive import record_table

    try:
        entry = record_table(path, loader(), name, driver)
    except Exception as exc:
        entry = {"status": "ERROR", "rows": 0, "message": str(exc)}
    log_event(
        report,
        log_path,
        meta,
        name,
        entry["status"],
        driver=driver,
        rows=entry.get("rows"),
        path=path,
        message=entry.get("message", ""),
    )


def get_pit_events(laps):
    df = pd.DataFrame(laps)

    if df.empty:
        return df.copy()

    if not {"PitInTime", "PitOutTime"}.issubset(df.columns):
        return pd.DataFrame()

    return df.loc[df["PitInTime"].notna() | df["PitOutTime"].notna()].copy()


def get_stints(laps):
    df = pd.DataFrame(laps)

    required = {
        "Driver",
        "Stint",
        "LapNumber",
        "Compound",
        "TyreLife",
    }

    if not required.issubset(df.columns):
        return pd.DataFrame()

    result = (
        df.groupby(
            ["Driver", "Stint"],
            dropna=False,
            sort=False,
        )
        .agg(
            first_lap=("LapNumber", "min"),
            last_lap=("LapNumber", "max"),
            lap_count=("LapNumber", "count"),
            compound=("Compound", "first"),
            tyre_life_start=("TyreLife", "min"),
            tyre_life_end=("TyreLife", "max"),
        )
        .reset_index()
    )
    extra = []
    for (driver, stint), stint_laps in df.groupby(
        ["Driver", "Stint"], dropna=False, sort=False
    ):
        group = stint_laps.sort_values("LapNumber")
        row = {
            "Driver": driver,
            "Stint": stint,
            "compound_sequence": json.dumps(
                group.Compound.drop_duplicates()
                .where(group.Compound.notna(), None)
                .tolist()
            ),
            "compound_count": group.Compound.nunique(dropna=True),
        }
        if "LapTime" in group:
            row["timed_lap_count"] = int(group.LapTime.notna().sum())
            row["timed_lap_duration"] = group.LapTime.sum(min_count=1)
        if {"LapStartTime", "Time"} <= set(group):
            row["first_lap_start"] = group.LapStartTime.min()
            row["last_lap_end"] = group.Time.max()
            row["elapsed_duration"] = row["last_lap_end"] - row["first_lap_start"]
        if "DriverNumber" in group:
            row["DriverNumber"] = group.DriverNumber.iloc[0]
        if "FreshTyre" in group:
            row["fresh_tyre_at_start"] = group.FreshTyre.iloc[0]
        extra.append(row)
    return (
        result.merge(pd.DataFrame(extra), on=["Driver", "Stint"], how="left")
        if extra
        else result
    )


def download_all(schedule, year):
    """Export and verify through the resumable FastF1-only archive engine."""
    from f1_project.fastf1_archive import ingest

    return ingest(schedule, int(year))
