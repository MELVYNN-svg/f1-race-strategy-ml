"""Resumable, source-compared FastF1 archive. No direct sports API calls."""

import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fastf1
import pandas as pd

from f1_project.pit_stops import build_pit_stops
from f1_project.quality import check_table, cross_checks, json_text, telemetry_alignment

LOG = logging.getLogger(__name__)
ROOT = Path("data/01_raw/fastf1")
REPORT = Path("data/08_reporting")
BACKUP = Path("data/00_backup/fastf1")
VERSION = 2
SESSION_TABLES = (
    "laps",
    "results",
    "weather",
    "track_status",
    "session_status",
    "race_control",
    "pit_events",
    "stints",
    "pit_stops",
    "session_info",
    "session_metadata",
    "drivers",
    "circuit_corners",
    "circuit_marshal_lights",
    "circuit_marshal_sectors",
    "circuit_rotation",
)
TERMINAL = {"COMPLETE", "SOURCE_UNAVAILABLE", "NOT_APPLICABLE"}


class SourceDiagnostics(logging.Handler):
    """Capture FastF1 soft exceptions without altering its network behavior."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.errors = []

    def emit(self, record):
        if record.name.startswith("fastf1") and record.exc_info:
            exc = record.exc_info[1]
            self.errors.append(
                {
                    "operation": record.getMessage(),
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def replace_file(source, target):
    """Windows readers/antivirus can briefly deny an otherwise atomic rename."""
    attempts = 7
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.05 * 2**attempt)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, default=str)
            stream.flush()
            os.fsync(stream.fileno())
        replace_file(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_parquet(path, frame, backup=True):
    """Validate complete new pages before preserving and replacing the original."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    original = ""
    try:
        frame.to_parquet(temp, index=False, engine="pyarrow")
        reread = pd.read_parquet(temp)
        pd.testing.assert_frame_equal(
            frame.reset_index(drop=True), reread, check_dtype=False
        )
        del reread
        if backup and path.exists():
            relative = (
                path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path(path.name)
            )
            original_path = (
                BACKUP / relative.parent / (relative.name + "." + sha256(path) + ".bak")
            )
            original_path.parent.mkdir(parents=True, exist_ok=True)
            if not original_path.exists():
                shutil.copy2(path, original_path)
            if sha256(path) != sha256(original_path):
                raise OSError("Backup checksum mismatch")
            original = str(original_path)
        replace_file(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return original


def expected_sessions(schedule, year):
    from f1_project.pipelines.data_ingestion.nodes import slug

    testing = 0
    for _, event in schedule.iterrows():
        is_test = event.get("EventFormat") == "testing"
        if is_test:
            testing += 1
        code = (
            f"test_{testing:02d}" if is_test else f"round_{int(event.RoundNumber):02d}"
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
            yield {
                "year": int(year),
                "event_code": code,
                "event": str(event.EventName),
                "round": int(event.RoundNumber),
                "session": name,
                "session_code": f"{number:02d}_{slug(name)}",
                "number": number,
                "testing_number": testing if is_test else 0,
                "event_row": event,
            }


def manifest_path(meta):
    return (
        REPORT
        / str(meta["year"])
        / "manifests"
        / f"{meta['event_code']}__{meta['session_code']}.json"
    )


def read_manifest(meta):
    path = manifest_path(meta)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def verified_manifest(manifest):
    if (
        manifest.get("version") != VERSION
        or manifest.get("fastf1_version") != fastf1.__version__
    ):
        return False
    records = manifest.get("records", [])
    if not records or manifest.get("load_error"):
        return False
    # Missing components and changed bytes always invalidate the checkpoint.
    if not (set(SESSION_TABLES) | {"car_data", "position"}) <= {
        r["dataset"] for r in records
    }:
        return False
    for row in records:
        if row["status"] not in TERMINAL:
            return False
        if row.get("sha256"):
            path = Path(row["path"])
            if not path.is_file() or sha256(path) != row["sha256"]:
                return False
    return True


def record_table(path, data, dataset, driver="", empty_status="SOURCE_UNAVAILABLE"):
    from f1_project.pipelines.data_ingestion.nodes import prepare

    row = {
        "dataset": dataset,
        "driver": str(driver),
        "path": str(path),
        "utc": utc_now(),
        "status": "ERROR",
        "rows": 0,
        "message": "",
        "source_rows": None,
    }
    try:
        if data is None:
            row["message"] = "FastF1 returned None; availability is not established"
            return row
        frame = prepare(data)
        row["source_rows"] = len(frame)
        row["source_schema"] = {c: str(t) for c, t in frame.dtypes.items()}
        if frame.empty:
            row["status"] = empty_status
            row["message"] = (
                "Empty object returned by FastF1 (or empty derived table); no fabricated observations"
            )
            if path.exists():
                row["status"] = "PARTIAL"
                row["message"] += "; older export retained pending review"
            return row
        issues, metrics = check_table(frame, dataset)
        row["issues"] = issues
        row["metrics"] = metrics
        equal = False
        if path.exists():
            try:
                old = prepare(pd.read_parquet(path))
                equal = old.equals(frame)
                if not equal:
                    row["previous_rows"] = len(old)
                    row["message"] = (
                        "Content/schema differs from FastF1; original backed up"
                    )
                    # Never downgrade a larger historical export automatically.
                    if len(old) > len(frame) or set(old) - set(frame):
                        row.update(
                            status="PARTIAL",
                            rows=len(old),
                            sha256=sha256(path),
                            message="Source regression (fewer rows/columns); original retained",
                        )
                        return row
            except Exception as exc:
                row["message"] = f"Unreadable original: {type(exc).__name__}: {exc}"
        if not equal:
            row["backup"] = atomic_parquet(path, frame)
        row.update(
            status="COMPLETE",
            rows=len(frame),
            sha256=sha256(path),
            action="verified_existing" if equal else "saved",
        )
        if any(issue["severity"] == "INVALID" for issue in issues):
            row["status"] = "PARTIAL"
            row["message"] += "; invalid source structure retained and flagged"
    except Exception as exc:
        row["message"] = f"{type(exc).__name__}: {exc}"
    return row


def retry_call(func, attempts=3, sleep=time.sleep):
    for attempt in range(attempts):
        try:
            return func()
        except Exception as exc:
            # Never bypass or repeatedly hammer a rate limiter.
            if "RateLimit" in type(exc).__name__ or attempt == attempts - 1:
                raise
            LOG.warning("Attempt %d/%d failed: %s", attempt + 1, attempts, exc)
            sleep(min(2 ** (attempt + 1), 30))


def export_session(session, meta, folder, checkpoint):
    from f1_project.pipelines.data_ingestion.nodes import get_pit_events, get_stints

    records = []

    def add(name, loader, driver="", empty_status="SOURCE_UNAVAILABLE"):
        path = (
            folder / name / f"{driver}.parquet"
            if driver
            else folder / f"{name}.parquet"
        )
        try:
            row = record_table(path, loader(), name, driver, empty_status)
        except Exception as exc:
            row = {
                "dataset": name,
                "driver": str(driver),
                "status": "ERROR",
                "path": str(path),
                "message": f"{type(exc).__name__}: {exc}",
                "utc": utc_now(),
                "rows": 0,
            }
        records.append(row)
        checkpoint(records)
        return row

    attributes = {
        "laps": "laps",
        "results": "results",
        "weather": "weather_data",
        "track_status": "track_status",
        "session_status": "session_status",
        "race_control": "race_control_messages",
    }
    for name, attr in attributes.items():
        add(name, lambda a=attr: getattr(session, a))
    add("session_info", lambda: pd.json_normalize(session.session_info))

    def session_metadata():
        return pd.DataFrame(
            [
                {
                    "t0_date": session.t0_date,
                    "session_start_time": session.session_start_time,
                    "total_laps": session.total_laps,
                    "name": session.name,
                    "date": session.date,
                    "f1_api_support": session.f1_api_support,
                    "fastf1_version": fastf1.__version__,
                }
            ]
        )

    add("session_metadata", session_metadata)
    add("drivers", lambda: pd.DataFrame({"DriverNumber": session.drivers}))
    add(
        "pit_events",
        lambda: get_pit_events(session.laps),
        empty_status="NOT_APPLICABLE",
    )
    add("stints", lambda: get_stints(session.laps))
    add(
        "pit_stops",
        lambda: build_pit_stops(session.laps, session.track_status),
        empty_status="NOT_APPLICABLE",
    )
    try:
        laps, results = pd.DataFrame(session.laps), pd.DataFrame(session.results)
        sport_issues = cross_checks(laps, results, meta["session"])
        for row in records:
            if row["dataset"] == "laps":
                row.setdefault("issues", []).extend(sport_issues)
                if any(i["code"] == "laps_below_classified" for i in sport_issues):
                    row["status"] = "PARTIAL"
                    row["message"] += "; fewer laps than own classification"
        active = (
            set(laps.DriverNumber.dropna().astype(str))
            if "DriverNumber" in laps
            else set()
        )
    except Exception:
        active = set()
    telemetry = {}
    for name, attr in [("car_data", "car_data"), ("position", "pos_data")]:
        try:
            mapping = getattr(session, attr)
            telemetry[name] = mapping
            expected = active | set(map(str, mapping))
            if not expected:
                add(name, lambda: None)
            for driver in sorted(expected):
                if driver not in mapping:
                    records.append(
                        {
                            "dataset": name,
                            "driver": driver,
                            "status": "SOURCE_UNAVAILABLE",
                            "path": str(folder / name / f"{driver}.parquet"),
                            "rows": 0,
                            "message": "Active driver absent from loaded FastF1 mapping",
                            "utc": utc_now(),
                        }
                    )
                else:
                    add(name, lambda d=driver, m=mapping: m[d], driver)
        except Exception as exc:
            records.append(
                {
                    "dataset": name,
                    "driver": "",
                    "status": "ERROR",
                    "path": str(folder / name),
                    "message": f"{type(exc).__name__}: {exc}",
                    "rows": 0,
                    "utc": utc_now(),
                }
            )
    if set(telemetry) == {"car_data", "position"}:
        for driver in set(telemetry["car_data"]) & set(telemetry["position"]):
            alignment = telemetry_alignment(
                telemetry["car_data"][driver], telemetry["position"][driver]
            )
            for row in records:
                if row["dataset"] == "car_data" and row["driver"] == str(driver):
                    row["alignment"] = alignment
    try:
        circuit = session.get_circuit_info()
        for part in ["corners", "marshal_lights", "marshal_sectors"]:
            add("circuit_" + part, lambda p=part: getattr(circuit, p))
        add("circuit_rotation", lambda: pd.DataFrame([{"rotation": circuit.rotation}]))
    except Exception as exc:
        for name in [
            "circuit_corners",
            "circuit_marshal_lights",
            "circuit_marshal_sectors",
            "circuit_rotation",
        ]:
            records.append(
                {
                    "dataset": name,
                    "driver": "",
                    "status": "ERROR",
                    "path": str(folder / f"{name}.parquet"),
                    "rows": 0,
                    "message": f"{type(exc).__name__}: {exc}",
                    "utc": utc_now(),
                }
            )
    checkpoint(records)
    return records


def ingest(
    schedule,
    year,
    *,
    max_sessions=None,
    refresh=False,
    skip_sessions=None,
    retry_unavailable=False,
):
    """One session in memory, existing cache reused, checkpoints per dataset."""
    from f1_project.pipelines.data_ingestion.nodes import configure_cache

    configure_cache()
    all_records = []
    processed = 0
    for meta in expected_sessions(schedule, year):
        key = (meta["event_code"], meta["session_code"])
        if skip_sessions and key in skip_sessions:
            continue
        simple = {k: v for k, v in meta.items() if k != "event_row"}
        previous = read_manifest(meta)
        folder = ROOT / str(year) / meta["event_code"] / meta["session_code"]
        retry_source = retry_unavailable and any(
            r.get("status") == "SOURCE_UNAVAILABLE" for r in previous.get("records", [])
        )
        if not refresh and not retry_source and verified_manifest(previous):
            all_records.extend({**simple, **r} for r in previous["records"])
            LOG.info(
                "Verified checkpoint: %s %s", meta["event_code"], meta["session_code"]
            )
            continue
        if max_sessions is not None and processed >= max_sessions:
            break
        processed += 1
        if shutil.disk_usage(ROOT.parent).free < 3 * 1024**3:
            raise OSError("Less than 3 GiB free; ingestion stopped before next session")
        record_table(
            folder.parent / "event.parquet", pd.DataFrame([meta["event_row"]]), "event"
        )
        manifest = {
            "version": VERSION,
            "fastf1_version": fastf1.__version__,
            "meta": simple,
            "started_utc": utc_now(),
            "records": [],
            "load_error": "in progress",
        }

        def checkpoint(records):
            manifest["records"] = records
            manifest["updated_utc"] = utc_now()
            atomic_json(manifest_path(meta), manifest)

        checkpoint([])
        LOG.warning(
            "Collecting %s %s %s", year, meta["event_code"], meta["session_code"]
        )
        try:
            diagnostics = SourceDiagnostics()

            def load():
                session = (
                    fastf1.get_testing_session(
                        int(year), meta["testing_number"], meta["number"]
                    )
                    if meta["testing_number"]
                    else fastf1.get_session(int(year), meta["round"], meta["number"])
                )
                logging.getLogger().addHandler(diagnostics)
                try:
                    session.load(laps=True, telemetry=True, weather=True, messages=True)
                except Exception as exc:
                    if type(exc).__name__ != "DataNotLoadedError":
                        raise
                    diagnostics.errors.append(
                        {
                            "operation": "Session.load",
                            "type": type(exc).__name__,
                            "message": str(exc),
                        }
                    )
                finally:
                    logging.getLogger().removeHandler(diagnostics)
                return session

            session = retry_call(load)
            manifest["load_error"] = ""
            records = export_session(session, meta, folder, checkpoint)
            manifest["source_diagnostics"] = diagnostics.errors
            unavailable = any(
                e["type"] == "SessionNotAvailableError" for e in diagnostics.errors
            )
            other_failure = any(
                e["type"] not in {"SessionNotAvailableError", "DataNotLoadedError"}
                for e in diagnostics.errors
            )
            if unavailable and not other_failure:
                for row in records:
                    if row["status"] == "ERROR" and any(
                        t in row.get("message", "")
                        for t in ["DataNotLoadedError", "SessionNotAvailableError"]
                    ):
                        row["status"] = "SOURCE_UNAVAILABLE"
                        row["message"] += (
                            "; FastF1 logged SessionNotAvailableError; see source_diagnostics"
                        )
            checkpoint(records)
            del session
            all_records.extend({**simple, **r} for r in records)
        except Exception as exc:
            manifest["load_error"] = f"{type(exc).__name__}: {exc}"
            checkpoint(manifest["records"])
            LOG.exception("Session failed")
            all_records.append(
                {
                    **simple,
                    "dataset": "session_load",
                    "status": "ERROR",
                    "message": manifest["load_error"],
                }
            )
            # Rate limits are a recoverable stop, not 100 more failing calls.
            if "RateLimit" in type(exc).__name__:
                atomic_json(
                    REPORT / "mission_2024_2025" / "network_cooldown.json",
                    {
                        "until_utc": (
                            datetime.now(timezone.utc) + timedelta(seconds=3605)
                        ).isoformat(),
                        "reason": manifest["load_error"],
                    },
                )
                break
        log = REPORT / str(year) / "fastf1_recovery.jsonl"
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json_text(manifest) + "\n")
    return pd.DataFrame(
        [
            {
                k: json_text(v) if isinstance(v, (dict, list)) else v
                for k, v in r.items()
            }
            for r in all_records
        ]
    )


def audit(schedule, year, *, deep=True):
    """Offline coverage reconciled with schedule and tamper-checked evidence."""
    coverage, quality = [], []
    for meta in expected_sessions(schedule, year):
        context = {
            k: meta[k]
            for k in ["year", "event_code", "event", "round", "session_code", "session"]
        }
        folder = ROOT / str(year) / meta["event_code"] / meta["session_code"]
        manifest = read_manifest(meta)
        evidence = {
            (r["dataset"], r.get("driver", "")): r for r in manifest.get("records", [])
        }
        drivers = set()
        for table in ["laps", "results"]:
            try:
                df = pd.read_parquet(
                    folder / f"{table}.parquet", columns=["DriverNumber"]
                )
                if table == "laps":
                    drivers.update(df.DriverNumber.dropna().astype(str))
            except Exception:
                pass
        expected = [(name, "") for name in SESSION_TABLES]
        for name in ["car_data", "position"]:
            present = {p.stem for p in (folder / name).glob("*.parquet")}
            source = {d for (n, d) in evidence if n == name and d}
            expected.extend(
                (name, d) for d in sorted(drivers | present | source or {""})
            )
        for name, driver in expected:
            path = (
                folder / name / f"{driver}.parquet"
                if driver
                else folder / f"{name}.parquet"
            )
            proof = evidence.get((name, driver), {})
            row = {
                **context,
                "dataset": name,
                "driver": driver,
                "path": str(path),
                "status": "MISSING",
                "rows": 0,
                "message": "No local export",
                "source_rows": proof.get("source_rows"),
            }
            if not path.exists():
                if proof.get("status") in {
                    "SOURCE_UNAVAILABLE",
                    "NOT_APPLICABLE",
                    "ERROR",
                }:
                    row.update(status=proof["status"], message=proof.get("message", ""))
                elif manifest.get("load_error"):
                    row.update(status="ERROR", message=manifest["load_error"])
            else:
                try:
                    df = pd.read_parquet(path)
                    digest = sha256(path)
                    valid_proof = (
                        manifest.get("version") == VERSION
                        and proof.get("sha256") == digest
                    )
                    row.update(
                        rows=len(df),
                        bytes=path.stat().st_size,
                        sha256=digest,
                        schema=json_text({c: str(t) for c, t in df.dtypes.items()}),
                    )
                    row["status"] = (
                        proof.get("status", "PARTIAL") if valid_proof else "PARTIAL"
                    )
                    row["message"] = (
                        proof.get("message", "")
                        if valid_proof
                        else "Source completeness not verified (legacy or changed file)"
                    )
                    if df.empty:
                        row.update(status="PARTIAL", message="Empty local export")
                    if deep:
                        issues, metrics = check_table(df, name)
                        row["metrics"] = json_text(metrics)
                        if any(i["severity"] == "INVALID" for i in issues):
                            row["status"] = "PARTIAL"
                        quality.extend(
                            {**context, "dataset": name, "driver": driver, **i}
                            for i in issues
                        )
                    if valid_proof:
                        row["alignment"] = json_text(proof.get("alignment", {}))
                    del df
                except Exception as exc:
                    row.update(status="ERROR", message=f"{type(exc).__name__}: {exc}")
            coverage.append(row)
        try:
            issues = cross_checks(
                pd.read_parquet(folder / "laps.parquet"),
                pd.read_parquet(folder / "results.parquet"),
                meta["session"],
            )
            quality.extend(
                {**context, "dataset": "laps", "driver": "", **i} for i in issues
            )
        except (OSError, ValueError):
            pass
    return pd.DataFrame(coverage), pd.DataFrame(
        quality,
        columns=[
            "year",
            "event_code",
            "event",
            "round",
            "session_code",
            "session",
            "dataset",
            "driver",
            "code",
            "count",
            "severity",
            "detail",
        ],
    )


def write_audit(schedule, year, deep=True):
    coverage, quality = audit(schedule, year, deep=deep)
    directory = REPORT / str(year)
    atomic_parquet(directory / "fastf1_coverage.parquet", coverage, backup=False)
    atomic_parquet(directory / "fastf1_quality.parquet", quality, backup=False)
    coverage.to_csv(directory / "fastf1_coverage.csv", index=False)
    quality.to_csv(directory / "fastf1_quality.csv", index=False)
    session_rows = []
    for (event, session), group in coverage.groupby(
        ["event_code", "session_code"], sort=False
    ):
        statuses = set(group.status)
        if statuses <= {"COMPLETE", "NOT_APPLICABLE"}:
            status = "COMPLETE"
        elif statuses == {"MISSING"}:
            status = "MISSING"
        elif "ERROR" in statuses:
            status = "ERROR"
        else:
            status = "PARTIAL"
        session_rows.append(
            {
                "year": year,
                "event_code": event,
                "session_code": session,
                "status": status,
                "dataset_status_counts": json_text(
                    group.status.value_counts().to_dict()
                ),
            }
        )
    atomic_parquet(
        directory / "fastf1_session_coverage.parquet",
        pd.DataFrame(session_rows),
        backup=False,
    )
    driver_rows = driver_inventory(schedule, year, coverage)
    atomic_parquet(
        directory / "fastf1_driver_coverage.parquet", driver_rows, backup=False
    )
    driver_rows.to_csv(directory / "fastf1_driver_coverage.csv", index=False)
    events = event_inventory(schedule, year)
    atomic_parquet(directory / "fastf1_event_coverage.parquet", events, backup=False)
    schemas = coverage.loc[
        coverage.get("schema", pd.Series(index=coverage.index, dtype=object)).notna()
    ]
    if not schemas.empty:
        schema_report = (
            schemas.groupby(["dataset", "schema"], dropna=False)
            .agg(files=("path", "size"))
            .reset_index()
        )
        atomic_parquet(
            directory / "fastf1_schemas.parquet", schema_report, backup=False
        )
    counts = coverage.status.value_counts().to_dict()
    atomic_json(
        directory / "fastf1_audit_summary.json",
        {
            "year": year,
            "utc": utc_now(),
            "status_counts": counts,
            "expected_sessions": len(list(expected_sessions(schedule, year))),
            "quality_issues": len(quality),
            "complete_definition": "Export equals FastF1 return, verified checksum; not proof of source physical completeness",
        },
    )
    return coverage, quality


def event_inventory(schedule, year):
    """Compare event metadata with the same FastF1 season calendar."""
    from f1_project.pipelines.data_ingestion.nodes import prepare
    from f1_project.pipelines.data_preparation.nodes import normalize_table

    rows = []
    seen = set()
    for meta in expected_sessions(schedule, year):
        event = meta["event_code"]
        if event in seen:
            continue
        seen.add(event)
        path = ROOT / str(year) / event / "event.parquet"
        row = {
            "year": year,
            "event_code": event,
            "dataset": "event",
            "path": str(path),
            "status": "MISSING",
            "message": "",
        }
        if path.exists():
            try:
                frame = normalize_table(prepare(pd.read_parquet(path)), "event")
                expected = normalize_table(
                    prepare(pd.DataFrame([meta["event_row"]])), "event"
                )
                row.update(
                    status="COMPLETE" if frame.equals(expected) else "PARTIAL",
                    rows=len(frame),
                    sha256=sha256(path),
                )
                if row["status"] == "PARTIAL":
                    row["message"] = (
                        "Event metadata differs from current FastF1 calendar"
                    )
            except Exception as exc:
                row.update(status="ERROR", message=f"{type(exc).__name__}: {exc}")
        rows.append(row)
    return pd.DataFrame(rows)


def prepare_local(schedule, year):
    """Reuse Kedro preparation functions and publish their outputs atomically."""
    from f1_project.pipelines.data_preparation.nodes import (
        build_inventory,
        build_sessions,
        concatenate_tables,
    )

    root = ROOT / str(year)
    partitions = {
        p.relative_to(root).with_suffix("").as_posix(): (
            lambda path=p: pd.read_parquet(path)
        )
        for p in root.rglob("*.parquet")
    }
    tables = concatenate_tables(partitions, year)
    primary = Path("data/03_primary/fastf1") / str(year)
    for name, table in tables.items():
        atomic_parquet(
            primary / (name.removeprefix("fastf1_") + ".parquet"), table, backup=False
        )
    inventory = build_inventory(partitions, year)
    atomic_parquet(
        REPORT / str(year) / "fastf1_inventory.parquet", inventory, backup=False
    )
    atomic_parquet(
        REPORT / str(year) / "fastf1_sessions.parquet",
        build_sessions(inventory, schedule),
        backup=False,
    )


def manifest_report(schedule, year):
    """Full report across all batches, including sessions skipped by checkpoints."""
    rows = []
    for meta in expected_sessions(schedule, year):
        proof = read_manifest(meta)
        context = {k: v for k, v in meta.items() if k != "event_row"}
        rows.extend({**context, **r} for r in proof.get("records", []))
        if proof.get("load_error"):
            rows.append(
                {
                    **context,
                    "dataset": "session_load",
                    "status": "ERROR",
                    "message": proof["load_error"],
                }
            )
    return pd.DataFrame(
        [
            {
                k: json_text(v) if isinstance(v, (dict, list)) else v
                for k, v in row.items()
            }
            for row in rows
        ]
    )


def driver_inventory(schedule, year, coverage):
    """Session-local identities, participation evidence and per-driver coverage."""
    rows = []
    for meta in expected_sessions(schedule, year):
        folder = ROOT / str(year) / meta["event_code"] / meta["session_code"]
        frames = {}
        for name in ("laps", "results"):
            try:
                frames[name] = pd.read_parquet(folder / f"{name}.parquet")
            except (OSError, ValueError):
                frames[name] = pd.DataFrame()
        local = coverage.loc[
            coverage.event_code.eq(meta["event_code"])
            & coverage.session_code.eq(meta["session_code"])
        ]
        drivers = set(local.driver.dropna().astype(str)) - {""}
        for frame in frames.values():
            if "DriverNumber" in frame:
                drivers.update(frame.DriverNumber.dropna().astype(str))
        for driver in sorted(drivers):
            selected = {}
            for name, frame in frames.items():
                selected[name] = (
                    frame.loc[frame.DriverNumber.astype(str).eq(driver)]
                    if "DriverNumber" in frame
                    else pd.DataFrame()
                )
            result, lap = selected["results"], selected["laps"]
            identity = result.iloc[0] if not result.empty else pd.Series(dtype=object)
            context = {
                "year": year,
                "event_code": meta["event_code"],
                "session_code": meta["session_code"],
                "driver": driver,
                "abbreviation": identity.get("Abbreviation"),
                "full_name": identity.get("FullName"),
                "team": identity.get("TeamName"),
                "result_status": identity.get("Status"),
                "observed_laps": len(lap),
                "participation": "LAPS_OBSERVED" if len(lap) else "NO_LAP_OBSERVED",
            }
            dns = str(identity.get("Status", "")).lower() in {
                "did not start",
                "did not qualify",
                "withdrew",
            }
            for name in ("laps", "results", "car_data", "position"):
                subset = local.loc[
                    local.dataset.eq(name)
                    & local.driver.eq(
                        driver if name in {"car_data", "position"} else ""
                    )
                ]
                status = subset.iloc[0].status if not subset.empty else "MISSING"
                count = (
                    len(selected[name])
                    if name in selected
                    else (int(subset.iloc[0].rows) if not subset.empty else 0)
                )
                if name == "laps" and not len(lap) and dns:
                    status = "NOT_APPLICABLE"
                elif name in selected and count == 0 and status == "COMPLETE":
                    status = "SOURCE_UNAVAILABLE"
                if (
                    name in {"car_data", "position"}
                    and count == 0
                    and not len(lap)
                    and dns
                ):
                    status = "NOT_APPLICABLE"
                rows.append(
                    {**context, "dataset": name, "status": status, "rows": count}
                )
    return pd.DataFrame(
        rows,
        columns=[
            "year",
            "event_code",
            "session_code",
            "driver",
            "abbreviation",
            "full_name",
            "team",
            "result_status",
            "observed_laps",
            "participation",
            "dataset",
            "status",
            "rows",
        ],
    )
