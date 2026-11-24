"""Expose les tables de saison sans charger la telemetrie en memoire."""

import re
from collections.abc import Callable
from pathlib import PurePosixPath

import pandas as pd

SESSION_TABLES = (
    "laps",
    "results",
    "weather",
    "stints",
    "pit_events",
    "track_status",
    "session_status",
    "race_control",
    "circuit_corners",
    "circuit_marshal_lights",
    "circuit_marshal_sectors",
    "circuit_rotation",
    "session_info",
    "session_metadata",
    "drivers",
    "pit_stops",
)
TABLES = ("event", *SESSION_TABLES)
CONTEXT_COLUMNS = ["year", "event_code", "round_number", "session_code", "session_name"]
INVENTORY_COLUMNS = [*CONTEXT_COLUMNS, "table", "driver_number", "partition"]


def partition_metadata(partition: str, year: int) -> dict | None:
    """Decode les chemins produits par l'ingestion, pas le cache FastF1."""
    parts = PurePosixPath(partition.replace("\\", "/")).parts
    if len(parts) < 2 or not re.fullmatch(r"(?:round|test)_\d+", parts[0]):  # noqa: PLR2004
        return None
    event = parts[0]
    session = ""
    driver = ""
    if len(parts) == 2 and parts[1] == "event":  # noqa: PLR2004
        table = "event"
    elif len(parts) == 3 and re.fullmatch(r"\d+_.+", parts[1]):  # noqa: PLR2004
        session, table = parts[1:]
    elif (
        len(parts) == 4  # noqa: PLR2004
        and re.fullmatch(r"\d+_.+", parts[1])
        and parts[2] in {"car_data", "position"}
    ):
        session, table, driver = parts[1:]
    else:
        return None
    return {
        "year": int(year),
        "event_code": event,
        "round_number": int(event.split("_")[1]) if event.startswith("round_") else 0,
        "session_code": session,
        "session_name": session.split("_", 1)[1] if session else "",
        "table": table,
        "driver_number": driver,
        "partition": partition,
    }


def build_inventory(partitions: dict[str, Callable], year: int) -> pd.DataFrame:
    """Liste les fichiers disponibles sans appeler leurs fonctions de lecture."""
    rows = [
        meta
        for key in sorted(partitions)
        if (meta := partition_metadata(key, year)) is not None
    ]
    return pd.DataFrame(rows, columns=INVENTORY_COLUMNS)


def normalize_table(frame: pd.DataFrame, table: str) -> pd.DataFrame:
    """Harmonise les types qui divergent dans les exports deja installes.

    Aucune conversion silencieuse des valeurs inconnues : une valeur inattendue
    fait echouer la preparation au lieu de devenir une donnee manquante.
    """
    frame = frame.copy()
    for boolean in (
        "IsPersonalBest",
        "IsAccurate",
        "Deleted",
        "FastF1Generated",
        "FreshTyre",
        "Rainfall",
        "is_estimated",
    ):
        if boolean not in frame:
            continue
        values = frame[boolean].astype("string").str.lower()
        if not values.dropna().isin(["true", "false"]).all():
            raise ValueError(f"Valeur {boolean} inconnue : attendu True/False/null")
        frame[boolean] = values.map({"true": True, "false": False}).astype("boolean")
    for column in ("Date", "LapStartDate", "t0_date", "date"):
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], utc=True)
    if table == "session_metadata" and "total_laps" in frame:
        frame["total_laps"] = pd.to_numeric(frame["total_laps"], errors="raise").astype(
            "Int64"
        )
    if "Time" in frame and pd.api.types.is_datetime64_any_dtype(frame["Time"]):
        frame["Time"] = pd.to_datetime(frame["Time"], utc=True)
    if table == "race_control":
        for column in ("Lap", "Sector"):
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="raise").astype(
                    "Int64"
                )
    if table == "event":
        for column in frame:
            if re.fullmatch(r"Session\dDate(?:Utc)?", column):
                frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def concatenate_tables(partitions: dict[str, Callable], year: int) -> dict:
    """Reunit chaque petite table et conserve son contexte de session.

    Les durees source sont conservees. Les booleens, numeros de tour/secteur
    et dates d'evenement sont harmonises. Aucun fichier car_data/position
    n'est lu. Les tables absentes restent des tables vides.
    """
    frames = {table: [] for table in TABLES}
    for key in sorted(partitions):
        meta = partition_metadata(key, year)
        if meta is None or meta["table"] not in frames or meta["driver_number"]:
            continue
        frame = normalize_table(partitions[key](), meta["table"])
        for column in CONTEXT_COLUMNS:
            frame[column] = meta[column]
        frames[meta["table"]].append(frame)
    return {
        f"fastf1_{'events' if table == 'event' else table}": (
            pd.concat(items, ignore_index=True, sort=False)
            if items
            else pd.DataFrame(columns=CONTEXT_COLUMNS)
        )
        for table, items in frames.items()
    }


def build_sessions(inventory: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """Compare les sessions attendues au contenu actuel, pas a un ancien log.

    Les indicateurs signalent la presence de fichiers, sans promettre leur
    exhaustivite ni la qualite scientifique de leurs lignes.
    """
    rows = []
    testing_number = 0
    for _, event in schedule.iterrows():
        is_testing = event["EventFormat"] == "testing"
        if is_testing:
            testing_number += 1
        event_code = (
            f"test_{testing_number:02d}"
            if is_testing
            else f"round_{int(event['RoundNumber']):02d}"
        )
        for number in range(1, 6):
            name = event.get(f"Session{number}")
            if not isinstance(name, str) or name.strip().lower() in {
                "",
                "none",
                "nan",
                "nat",
                "<na>",
            }:
                continue
            slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            session_code = f"{number:02d}_{slug}"
            files = inventory.loc[
                inventory["event_code"].eq(event_code)
                & inventory["session_code"].eq(session_code)
            ]
            counts = files["table"].value_counts()
            rows.append(
                {
                    "event_code": event_code,
                    "event_name": event["EventName"],
                    "round_number": int(event["RoundNumber"]),
                    "session_code": session_code,
                    "session_name": slug,
                    "has_laps": bool(counts.get("laps", 0)),
                    "has_results": bool(counts.get("results", 0)),
                    "car_data_files": int(counts.get("car_data", 0)),
                    "position_files": int(counts.get("position", 0)),
                    "file_count": len(files),
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "event_code",
            "event_name",
            "round_number",
            "session_code",
            "session_name",
            "has_laps",
            "has_results",
            "car_data_files",
            "position_files",
            "file_count",
        ],
    )
