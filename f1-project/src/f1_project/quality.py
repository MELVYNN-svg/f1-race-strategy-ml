"""Non-destructive FastF1 checks. Flags are evidence, never deletion rules."""

import json

import numpy as np
import pandas as pd

CLOCK_TOLERANCE_S = 0.002

REQUIRED = {
    "laps": {"DriverNumber", "LapNumber", "Time", "LapTime"},
    "results": {"DriverNumber"},
    "car_data": {"Date", "SessionTime", "Speed", "RPM", "nGear"},
    "position": {"Date", "SessionTime", "X", "Y", "Z", "Status"},
    "weather": {"Time", "AirTemp", "TrackTemp"},
    "track_status": {"Time", "Status"},
    "session_status": {"Time", "Status"},
    "race_control": {"Time", "Message"},
}


def check_table(frame, dataset):
    """Return compact issues and metrics; retain every source observation.

    Thresholds are screening limits, not sport rules. A >10 s telemetry gap
    includes garage periods; it does not establish loss of on-track samples.
    """
    issues = []
    metrics = {
        "rows": len(frame),
        "nulls": frame.isna().sum().to_dict(),
        "schema": {c: str(t) for c, t in frame.dtypes.items()},
    }
    for column in (
        "Date",
        "Time",
        "SessionTime",
        "LapStartTime",
        "LapStartDate",
        "LapNumber",
    ):
        if column in frame and frame[column].notna().any():
            metrics[column + "_min"] = str(frame[column].min())
            metrics[column + "_max"] = str(frame[column].max())
    if "DriverNumber" in frame:
        metrics["driver_rows"] = (
            frame.DriverNumber.astype("string").value_counts().to_dict()
        )

    def flag(code, count, detail="", severity="REVIEW"):
        if count:
            issues.append(
                {
                    "code": code,
                    "count": int(count),
                    "severity": severity,
                    "detail": detail,
                }
            )

    missing = REQUIRED.get(dataset, set()) - set(frame.columns)
    flag("missing_columns", len(missing), ",".join(sorted(missing)), "INVALID")
    flag("duplicate_rows", frame.duplicated().sum())
    if frame.empty:
        return issues, metrics
    for col in ["LapTime", "Sector1Time", "Sector2Time", "Sector3Time"]:
        if col in frame:
            if not pd.api.types.is_timedelta64_dtype(frame[col]):
                flag("duration_type", 1, col, "INVALID")
            else:
                flag(
                    "negative_duration",
                    frame[col].lt(pd.Timedelta(0)).sum(),
                    col,
                    "INVALID",
                )
    if dataset == "laps":
        if {"DriverNumber", "LapNumber"} <= set(frame):
            flag(
                "duplicate_driver_lap",
                frame.duplicated(["DriverNumber", "LapNumber"]).sum(),
            )
            for driver, group in frame.groupby("DriverNumber"):
                lap = pd.to_numeric(group.LapNumber, errors="coerce")
                flag("lap_order", lap.diff().lt(0).sum(), str(driver))
                flag(
                    "lap_number_gap", lap.sort_values().diff().gt(1).sum(), str(driver)
                )
                ordered = group.sort_values("LapNumber")
                if "Time" in ordered and pd.api.types.is_timedelta64_dtype(
                    ordered.Time
                ):
                    flag(
                        "lap_time_order",
                        ordered.Time.diff().lt(pd.Timedelta(0)).sum(),
                        str(driver),
                    )
                if "Stint" in ordered:
                    flag(
                        "stint_decreases",
                        pd.to_numeric(ordered.Stint, errors="coerce")
                        .diff()
                        .lt(0)
                        .sum(),
                        str(driver),
                    )
                if {"Stint", "Compound"} <= set(ordered):
                    changes = ordered.groupby("Stint").Compound.nunique(dropna=True)
                    flag(
                        "compound_changes_within_stint",
                        changes.gt(1).sum(),
                        str(driver),
                    )
        sectors = ["Sector1Time", "Sector2Time", "Sector3Time"]
        if set(["LapTime", *sectors]) <= set(frame) and all(
            pd.api.types.is_timedelta64_dtype(frame[c]) for c in ["LapTime", *sectors]
        ):
            complete = frame[["LapTime", *sectors]].notna().all(axis=1)
            delta = (
                (
                    frame[sectors[0]]
                    + frame[sectors[1]]
                    + frame[sectors[2]]
                    - frame.LapTime
                )
                .dt.total_seconds()
                .abs()
            )
            flag(
                "sector_sum_mismatch",
                (complete & delta.gt(0.005)).sum(),
                "tolerance 0.005 s; review IsAccurate and pit/flag context",
            )
        for col in ("IsAccurate", "Deleted", "FastF1Generated"):
            if col in frame:
                values = frame[col].astype("string").str.lower()
                flag(
                    "invalid_boolean",
                    (~values.dropna().isin(["true", "false"])).sum(),
                    col,
                    "INVALID",
                )
                metrics[col + "_true"] = int(values.eq("true").sum())
    if dataset in {"car_data", "position"}:
        if "Date" in frame:
            date = pd.to_datetime(frame.Date, utc=True, errors="coerce")
            flag(
                "invalid_datetime",
                (date.isna() & frame.Date.notna()).sum(),
                "Date",
                "INVALID",
            )
            flag("timestamp_reversal", date.diff().lt(pd.Timedelta(0)).sum())
            flag("duplicate_timestamp", date.duplicated().sum())
            gaps = date.sort_values().diff().dt.total_seconds().dropna()
            metrics["gap_p50_s"] = float(gaps.median()) if len(gaps) else None
            metrics["gap_p99_s"] = float(gaps.quantile(0.99)) if len(gaps) else None
            metrics["gap_max_s"] = float(gaps.max()) if len(gaps) else None
            flag(
                "telemetry_gap_over_10s",
                gaps.gt(10).sum(),
                "Includes legitimate inactivity; no interpolation",
            )
            if "SessionTime" in frame and pd.api.types.is_timedelta64_dtype(
                frame.SessionTime
            ):
                origins = date - frame.SessionTime
                spread = (origins.max() - origins.min()).total_seconds()
                metrics["clock_origin_spread_s"] = spread
                flag(
                    "inconsistent_clock_origin",
                    spread > CLOCK_TOLERANCE_S,
                    "Date - SessionTime, tolerance 2 ms",
                )
        limits = {
            "Speed": (0, 400),
            "RPM": (0, 16000),
            "Throttle": (0, 100),
            "nGear": (0, 8),
            "DRS": (0, 14),
        }
        for col, (low, high) in limits.items():
            if col in frame:
                values = pd.to_numeric(frame[col], errors="coerce")
                flag(
                    "nonnumeric_channel",
                    (values.isna() & frame[col].notna()).sum(),
                    col,
                    "INVALID",
                )
                outliers = values.lt(low) | values.gt(high)
                if col == "Throttle":
                    # Documented FastF1 sentinel, not 104 percent physical throttle.
                    sentinel = values.eq(104)
                    flag(
                        "source_unavailable_value",
                        sentinel.sum(),
                        "Throttle=104 (documented FastF1 sentinel)",
                        "INFO",
                    )
                    outliers &= ~sentinel
                flag(
                    "channel_outlier",
                    outliers.sum(),
                    f"{col}: screening [{low}, {high}]",
                )
    return issues, metrics


def cross_checks(laps, results, session_name):
    """Use each driver's own classified laps; never compare a retiree to winner."""
    issues = []
    if not {"DriverNumber", "LapNumber"} <= set(laps) or "DriverNumber" not in results:
        return issues
    known = set(results.DriverNumber.dropna().astype(str))
    unknown = set(laps.DriverNumber.dropna().astype(str)) - known
    if unknown and known:
        issues.append(
            {
                "code": "driver_not_in_results",
                "severity": "REVIEW",
                "count": len(unknown),
                "detail": str(sorted(unknown)),
            }
        )
    if session_name in {"Race", "Sprint"} and "Laps" in results:
        for _, result in results.iterrows():
            expected = pd.to_numeric(result.Laps, errors="coerce")
            observed = pd.to_numeric(
                laps.loc[
                    laps.DriverNumber.astype(str).eq(str(result.DriverNumber)),
                    "LapNumber",
                ],
                errors="coerce",
            ).max()
            if (
                pd.notna(expected)
                and expected > 0
                and (pd.isna(observed) or observed < expected)
            ):
                issues.append(
                    {
                        "code": "laps_below_classified",
                        "severity": "REVIEW",
                        "count": 1,
                        "detail": f"driver={result.DriverNumber}; observed={observed}; classified={expected}",
                    }
                )
    if {"Team", "Driver"} <= set(laps) and {"TeamName", "Abbreviation"} <= set(results):
        for _, r in results.iterrows():
            group = laps.loc[laps.DriverNumber.astype(str).eq(str(r.DriverNumber))]
            for left, right in [("Team", "TeamName"), ("Driver", "Abbreviation")]:
                if pd.notna(r[right]) and not group.empty:
                    count = (group[left].notna() & group[left].ne(r[right])).sum()
                    if count:
                        issues.append(
                            {
                                "code": "driver_identity_mismatch",
                                "severity": "REVIEW",
                                "count": int(count),
                                "detail": f"{r.DriverNumber}: {left}",
                            }
                        )
    return issues


def telemetry_alignment(car, position):
    """Nearest real sample distances, without merging/interpolating channels."""
    if car.empty or position.empty or "Date" not in car or "Date" not in position:
        return {"status": "MISSING"}
    a = (
        pd.to_datetime(car.Date, utc=True)
        .dropna()
        .sort_values()
        .astype("int64")
        .to_numpy()
    )
    b = (
        pd.to_datetime(position.Date, utc=True)
        .dropna()
        .sort_values()
        .astype("int64")
        .to_numpy()
    )
    if not len(a) or not len(b):
        return {"status": "MISSING"}
    idx = np.searchsorted(b, a)
    delta = (
        np.minimum(
            abs(a - b[np.clip(idx, 0, len(b) - 1)]),
            abs(a - b[np.clip(idx - 1, 0, len(b) - 1)]),
        )
        / 1e9
    )
    return {
        "status": "MEASURED",
        "nearest_p50_s": float(np.median(delta)),
        "nearest_p99_s": float(np.quantile(delta, 0.99)),
        "outside_position_span": int(((a < b[0]) | (a > b[-1])).sum()),
    }


def json_text(value):
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
