"""python -m f1_project.fastf1_cli --years 2025 2024 --ingest."""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from f1_project.fastf1_archive import (
    REPORT,
    ROOT,
    atomic_json,
    atomic_parquet,
    ingest,
    manifest_report,
    prepare_local,
    retry_call,
    utc_now,
    write_audit,
)
from f1_project.pipelines.data_ingestion.nodes import get_schedule, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="+", type=int, default=[2025, 2024])
    parser.add_argument("--ingest", action="store_true")
    parser.add_argument(
        "--require-auth",
        action="store_true",
        help="Wait for a locally authenticated FastF1 account before collection",
    )
    parser.add_argument(
        "--retry-unavailable",
        action="store_true",
        help="Retry unavailable datasets after authentication, preserving complete-session checkpoints",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Recompare terminal checkpoints with FastF1 cache/source",
    )
    parser.add_argument("--max-sessions", type=int)
    parser.add_argument(
        "--wait-rate-limit",
        action="store_true",
        help="Wait one full hour after FastF1 rate limit; never bypass it",
    )
    parser.add_argument(
        "--shallow",
        action="store_true",
        help="Skip scientific checks; still read and hash every file",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    directory = REPORT / "mission_2024_2025"
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / "ingestion.lock"
    # OS releases this exclusive lock on crashes; the filename can safely persist.
    import msvcrt

    with lock.open("a+b") as handle:
        handle.seek(0)
        if handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        previous_state = {}
        try:
            previous_state = json.loads(
                (directory / "run_state.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            pass
        state = {
            "pid": os.getpid(),
            "started_utc": utc_now(),
            "years": args.years,
            "status": "RUNNING",
        }
        atomic_json(directory / "run_state.json", state)
        try:
            if args.ingest:
                until = None
                try:
                    cooldown = json.loads(
                        (directory / "network_cooldown.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    until = datetime.fromisoformat(cooldown["until_utc"])
                except (OSError, ValueError, KeyError):
                    if previous_state.get("phase") == "rate_limit_cooldown_3605s":
                        until = datetime.fromisoformat(
                            previous_state["updated_utc"]
                        ) + timedelta(seconds=3605)
                if until and until > datetime.now(timezone.utc):
                    atomic_json(
                        directory / "network_cooldown.json",
                        {
                            "until_utc": until.isoformat(),
                            "reason": "Preserved previous FastF1 rate-limit cooldown",
                        },
                    )
                    state.update(
                        phase="rate_limit_cooldown_3605s",
                        cooldown_until_utc=until.isoformat(),
                    )
                    atomic_json(directory / "run_state.json", state)
                    while datetime.now(timezone.utc) < until:
                        time.sleep(
                            min(
                                30,
                                max(
                                    0,
                                    (
                                        until - datetime.now(timezone.utc)
                                    ).total_seconds(),
                                ),
                            )
                        )
            if args.ingest and args.require_auth:
                while True:
                    probe = subprocess.run(
                        [sys.executable, "-m", "fastf1", "auth", "f1tv", "--status"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if (
                        probe.returncode == 0
                        and "Token Status: Expires" in probe.stdout
                    ):
                        break
                    state.update(
                        phase="awaiting_local_f1tv_authentication",
                        updated_utc=utc_now(),
                    )
                    atomic_json(directory / "run_state.json", state)
                    time.sleep(30)
            for year in args.years:
                state.update(year=year, phase="schedule")
                atomic_json(directory / "run_state.json", state)
                path = ROOT / str(year) / "schedule.parquet"
                if args.ingest:
                    schedule = retry_call(lambda y=year: get_schedule(y))
                    prepared = prepare(schedule)
                    if not path.exists() or not pd.read_parquet(path).equals(prepared):
                        atomic_parquet(path, prepared)
                else:
                    schedule = pd.read_parquet(path)
                if args.ingest:
                    attempted = set()
                    while True:
                        state.update(phase="ingestion", updated_utc=utc_now())
                        atomic_json(directory / "run_state.json", state)
                        result = ingest(
                            schedule,
                            year,
                            max_sessions=args.max_sessions,
                            refresh=args.refresh,
                            skip_sessions=attempted,
                            retry_unavailable=args.retry_unavailable,
                        )
                        atomic_parquet(
                            REPORT / str(year) / "fastf1_ingestion_report.parquet",
                            manifest_report(schedule, year),
                            backup=False,
                        )
                        limited = False
                        if not result.empty:
                            for key, group in result.groupby(
                                ["event_code", "session_code"]
                            ):
                                rate_error = (
                                    group["message"]
                                    .fillna("")
                                    .str.contains("RateLimit")
                                    .any()
                                )
                                if rate_error:
                                    limited = True
                                else:
                                    attempted.add(key)
                        if not limited or not args.wait_rate_limit:
                            break
                        until = datetime.now(timezone.utc) + timedelta(seconds=3605)
                        atomic_json(
                            directory / "network_cooldown.json",
                            {
                                "until_utc": until.isoformat(),
                                "reason": "FastF1 rate limit during collection or export",
                            },
                        )
                        state.update(
                            phase="rate_limit_cooldown_3605s",
                            updated_utc=utc_now(),
                            cooldown_until_utc=until.isoformat(),
                        )
                        atomic_json(directory / "run_state.json", state)
                        for _ in range(73):
                            time.sleep(3605 / 73)
                state.update(phase="audit", updated_utc=utc_now())
                atomic_json(directory / "run_state.json", state)
                coverage, _ = write_audit(schedule, year, deep=not args.shallow)
                state.setdefault("year_outcomes", {})[str(year)] = (
                    "COMPLETE"
                    if set(coverage.status) <= {"COMPLETE", "NOT_APPLICABLE"}
                    else "PARTIAL"
                )
                state.update(phase="preparation", updated_utc=utc_now())
                atomic_json(directory / "run_state.json", state)
                prepare_local(schedule, year)
            state.update(status="FINISHED", phase="done", finished_utc=utc_now())
            state["outcome"] = (
                "COMPLETE"
                if set(state.get("year_outcomes", {}).values()) == {"COMPLETE"}
                else "PARTIAL"
            )
        except BaseException as exc:
            state.update(
                status="INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ERROR",
                error=f"{type(exc).__name__}: {exc}",
                updated_utc=utc_now(),
            )
            raise
        finally:
            atomic_json(directory / "run_state.json", state)


if __name__ == "__main__":
    main()
