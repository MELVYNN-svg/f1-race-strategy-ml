
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import fastf1
import pandas as pd
import pyarrow.parquet as pq


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
    fastf1.Cache.enable_cache(str(CACHE))


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
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(text).lower()
    ).strip("_")


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
        pq.ParquetFile(str(path))
        return True
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
            ) + "\n"
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
    if valid_parquet(path):
        log_event(
            report,
            log_path,
            meta,
            name,
            "cached",
            driver=driver,
            path=path,
        )
        return

    temp_path = path.with_name(path.name + ".partial")

    try:
        data = loader()

        if data is None:
            log_event(
                report,
                log_path,
                meta,
                name,
                "missing",
                driver=driver,
            )
            return

        df = prepare(data)

        if df.empty and len(df.columns) == 0:
            log_event(
                report,
                log_path,
                meta,
                name,
                "missing",
                driver=driver,
            )
            return

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        df.to_parquet(
            temp_path,
            engine="pyarrow",
            index=False,
        )

        temp_path.replace(path)

        log_event(
            report,
            log_path,
            meta,
            name,
            "saved",
            driver=driver,
            rows=len(df),
            path=path,
        )

    except Exception as exc:
        temp_path.unlink(missing_ok=True)

        log_event(
            report,
            log_path,
            meta,
            name,
            "error",
            driver=driver,
            path=path,
            message=f"{type(exc).__name__}: {exc}",
        )


def get_pit_events(laps):
    df = pd.DataFrame(laps)

    if df.empty:
        return df.copy()

    if not {"PitInTime", "PitOutTime"}.issubset(df.columns):
        return pd.DataFrame()

    return df.loc[
        df["PitInTime"].notna()
        | df["PitOutTime"].notna()
    ].copy()


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

    return (
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


def download_all(schedule, year):
    configure_cache()

    year = int(year)
    report = []

    root = ROOT / str(year)

    log_path = (
        Path("data/08_reporting")
        / str(year)
        / "fastf1_progress.jsonl"
    )

    testing_number = 0
    total_events = len(schedule)

    for event_index, (_, event) in enumerate(
        schedule.iterrows(),
        start=1,
    ):
        is_testing = str(event["EventFormat"]) == "testing"

        if is_testing:
            testing_number += 1

        round_number = int(event["RoundNumber"])
        event_name = str(event["EventName"])

        if is_testing:
            event_code = f"test_{testing_number:02d}"
        else:
            event_code = f"round_{round_number:02d}"

        event_folder = root / event_code

        event_meta = {
            "year": year,
            "event": event_name,
            "round": round_number,
            "session": "event",
        }

        print(
            f"\nEVENT {event_index}/{total_events} : "
            f"{event_name}",
            flush=True,
        )

        save_table(
            event_folder / "event.parquet",
            lambda e=event: pd.DataFrame([e]),
            report,
            log_path,
            event_meta,
            "event",
        )

        for number in range(1, 6):
            session_name = event.get(f"Session{number}")

            if not isinstance(session_name, str):
                continue

            if not session_name.strip():
                continue

            session_code = (
                f"{number:02d}_{slug(session_name)}"
            )

            folder = event_folder / session_code

            meta = {
                "year": year,
                "event": event_name,
                "round": round_number,
                "session": session_name,
            }

            print(
                f"\nSESSION {number} : {session_name}",
                flush=True,
            )

            try:
                if is_testing:
                    session = fastf1.get_testing_session(
                        year,
                        testing_number,
                        number,
                    )
                else:
                    session = fastf1.get_session(
                        year,
                        round_number,
                        number,
                    )

                session.load(
                    laps=True,
                    telemetry=True,
                    weather=True,
                    messages=True,
                )

            except Exception as exc:
                log_event(
                    report,
                    log_path,
                    meta,
                    "session_load",
                    "error",
                    message=f"{type(exc).__name__}: {exc}",
                )
                continue

            tables = {
                "laps": lambda: session.laps,
                "results": lambda: session.results,
                "weather": lambda: session.weather_data,
                "track_status": lambda: session.track_status,
                "session_status": lambda: session.session_status,
                "race_control": lambda: session.race_control_messages,
                "pit_events": lambda: get_pit_events(session.laps),
                "stints": lambda: get_stints(session.laps),
            }

            for name, loader in tables.items():
                save_table(
                    folder / f"{name}.parquet",
                    loader,
                    report,
                    log_path,
                    meta,
                    name,
                )

            for dataset, attribute in [
                ("car_data", "car_data"),
                ("position", "pos_data"),
            ]:
                try:
                    driver_data = getattr(
                        session,
                        attribute,
                    )

                    if not driver_data:
                        log_event(
                            report,
                            log_path,
                            meta,
                            dataset,
                            "missing",
                        )
                        continue

                    for driver, df in driver_data.items():
                        save_table(
                            folder
                            / dataset
                            / f"{driver}.parquet",
                            lambda d=df: d,
                            report,
                            log_path,
                            meta,
                            dataset,
                            driver=str(driver),
                        )

                except Exception as exc:
                    log_event(
                        report,
                        log_path,
                        meta,
                        dataset,
                        "error",
                        message=f"{type(exc).__name__}: {exc}",
                    )

            try:
                circuit = session.get_circuit_info()

                for section in [
                    "corners",
                    "marshal_lights",
                    "marshal_sectors",
                ]:
                    save_table(
                        folder / f"circuit_{section}.parquet",
                        lambda s=section: getattr(circuit, s),
                        report,
                        log_path,
                        meta,
                        f"circuit_{section}",
                    )

                save_table(
                    folder / "circuit_rotation.parquet",
                    lambda: pd.DataFrame(
                        [{"rotation": circuit.rotation}]
                    ),
                    report,
                    log_path,
                    meta,
                    "circuit_rotation",
                )

            except Exception as exc:
                log_event(
                    report,
                    log_path,
                    meta,
                    "circuit_info",
                    "error",
                    message=f"{type(exc).__name__}: {exc}",
                )

    result = pd.DataFrame(report, columns=COLUMNS)

    if not result.empty:
        print(
            result.groupby(["dataset", "status"]).size(),
            flush=True,
        )

    return result
