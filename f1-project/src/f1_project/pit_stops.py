"""Derived pit visits: timestamp pairing, never stationary tyre-change time."""

import pandas as pd

COLUMNS = [
    "DriverNumber",
    "pit_in",
    "pit_out",
    "in_lap",
    "out_lap",
    "lane_elapsed",
    "compound_before",
    "compound_after",
    "stint_before",
    "stint_after",
    "pair_status",
    "track_status_codes",
    "context",
    "is_estimated",
]


def build_pit_stops(laps, track_status=None):
    rows = []
    required = {"DriverNumber", "PitInTime", "PitOutTime"}
    if not required <= set(laps):
        return pd.DataFrame(columns=COLUMNS)
    track_status = pd.DataFrame() if track_status is None else track_status
    for driver, group in laps.groupby("DriverNumber", sort=False):
        events = []
        for _, lap in group.iterrows():
            for col, kind in [("PitInTime", "in"), ("PitOutTime", "out")]:
                if pd.notna(lap[col]):
                    events.append((lap[col], kind, lap))
        pending = None

        def append(entry, exit_):
            before = entry[2] if entry else pd.Series(dtype=object)
            after = exit_[2] if exit_ else pd.Series(dtype=object)
            tin = entry[0] if entry else pd.NaT
            tout = exit_[0] if exit_ else pd.NaT
            codes = ""
            if entry and exit_ and {"Time", "Status"} <= set(track_status):
                status = track_status.sort_values("Time")
                during = status.loc[status.Time.gt(tin) & status.Time.le(tout)]
                initial = status.loc[status.Time.le(tin)].tail(1)
                codes = "|".join(
                    pd.concat([initial, during]).Status.astype(str).unique()
                )
            context = "UNKNOWN"
            if "5" in codes:
                context = "RED_FLAG_INTERVAL"
            elif any(code in codes for code in ["4", "6", "7"]):
                context = "SC_OR_VSC_INTERVAL"
            elif codes == "1":
                context = "GREEN"
            elif codes:
                context = "OTHER_FLAGS"
            rows.append(
                {
                    "DriverNumber": str(driver),
                    "pit_in": tin,
                    "pit_out": tout,
                    "in_lap": before.get("LapNumber"),
                    "out_lap": after.get("LapNumber"),
                    "lane_elapsed": tout - tin if entry and exit_ else pd.NaT,
                    "compound_before": before.get("Compound"),
                    "compound_after": after.get("Compound"),
                    "stint_before": before.get("Stint"),
                    "stint_after": after.get("Stint"),
                    "pair_status": "PAIRED"
                    if entry and exit_
                    else ("UNMATCHED_IN" if entry else "UNMATCHED_OUT"),
                    "track_status_codes": codes,
                    "context": context,
                    "is_estimated": True,
                }
            )

        for event in sorted(events, key=lambda e: e[0]):
            if event[1] == "in":
                if pending:
                    append(pending, None)
                pending = event
            else:
                append(pending, event)
                pending = None
        if pending:
            append(pending, None)
    result = pd.DataFrame(rows, columns=COLUMNS)
    for col in ["pit_in", "pit_out", "lane_elapsed"]:
        # An all-NaT column is inferred as datetime, despite representing durations.
        result[col] = pd.Series(
            pd.array(result[col].tolist(), dtype="timedelta64[ns]"), index=result.index
        )
    return result
