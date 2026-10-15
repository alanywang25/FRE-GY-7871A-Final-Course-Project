"""Archive ALFRED vintage histories for the project's added macro controls.

This collector intentionally distinguishes ALFRED-backed series from series
that only exist in current-value FRED.  It never substitutes revised FRED
values for a missing vintage archive; those series remain in the primary-source
collection queue.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
BASE = ROOT / "data/external/vintages"
RAW = BASE / "raw"
PROCESSED = BASE / "processed"
LONG_OUT = PROCESSED / "alfred_control_vintage_observations.csv"
SNAPSHOT_OUT = PROCESSED / "control_vintage_snapshot_panel.csv"
MANIFEST = PROCESSED / "control_vintage_manifest.json"
API = "https://api.stlouisfed.org/fred/series/observations"

# The first five are controls used or monitored by the extended specification;
# PCEPI is also needed to calculate a vintage-consistent cumulative price level.
SERIES = {
    "U6RATE": {"control": "underemployment_u6", "frequency": "monthly", "transform": "level"},
    "DSPIC96": {"control": "real_disposable_income", "frequency": "monthly", "transform": "year_over_year"},
    "PCEPI": {"control": "pce_price_index", "frequency": "monthly", "transform": "cumulative_since_2010"},
    "TDSP": {"control": "debt_service_ratio", "frequency": "quarterly", "transform": "level_carry_forward_after_release"},
    "USEPUINDXM": {"control": "policy_uncertainty", "frequency": "monthly", "transform": "level"},
    "FIXHAI": {"control": "housing_affordability", "frequency": "monthly", "transform": "level"},
}
# EPU's daily download page is not needed for the monthly model control.  Query
# the monthly series at each decision-date instead, which both avoids the UI
# and preserves the value publicly available at that cutoff.
POINT_IN_TIME_SERIES = {"USEPUINDXM"}
POINT_IN_TIME_FIRST_AVAILABLE = {"USEPUINDXM": pd.Timestamp("2013-06-03")}


def read_key() -> str:
    if not ENV.exists():
        raise FileNotFoundError("Missing .env; add FRED_API_KEY locally.")
    values = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    key = values.get("FRED_API_KEY", "")
    if not key:
        raise ValueError("FRED_API_KEY is not set in .env.")
    return key


def request_full_vintage_history(series_id: str, start: str, end: str, key: str) -> tuple[dict, bytes]:
    params = {
        "series_id": series_id, "api_key": key, "file_type": "json",
        "realtime_start": start, "realtime_end": end,
        "observation_start": start, "observation_end": end,
        "output_type": "2", "limit": "100000", "sort_order": "asc",
    }
    with urlopen(f"{API}?{urlencode(params)}", timeout=120) as response:  # nosec B310: fixed HTTPS API
        body = response.read()
    return json.loads(body), body


def request_point_in_time(series_id: str, cutoff: str, start: str, key: str) -> tuple[dict, bytes]:
    """Return the complete series as ALFRED exposed it on one cutoff date."""
    params = {
        "series_id": series_id, "api_key": key, "file_type": "json",
        "realtime_start": cutoff, "realtime_end": cutoff,
        "observation_start": start, "observation_end": cutoff,
        "sort_order": "asc",
    }
    with urlopen(f"{API}?{urlencode(params)}", timeout=120) as response:  # nosec B310: fixed HTTPS API
        body = response.read()
    return json.loads(body), body


def annual_windows(start: str, end: str) -> list[tuple[str, str]]:
    """Keep high-frequency revision histories below ALFRED's 2,000-vintage cap."""
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    windows = []
    for year in range(first.year, last.year + 1):
        left = max(first, pd.Timestamp(f"{year}-01-01"))
        right = min(last, pd.Timestamp(f"{year}-12-31"))
        windows.append((left.date().isoformat(), right.date().isoformat()))
    return windows


def monthly_windows(start: str, end: str) -> list[tuple[str, str]]:
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    return [
        (max(first, month).date().isoformat(), min(last, month + pd.offsets.MonthEnd(0)).date().isoformat())
        for month in pd.date_range(first.to_period("M").to_timestamp(), last.to_period("M").to_timestamp(), freq="MS")
    ]


def expand_output_type_2(series_id: str, payload: dict, meta: dict) -> list[dict[str, str]]:
    """Turn ALFRED's one-column-per-vintage JSON response into long records."""
    prefix = f"{series_id}_"
    rows = []
    for observation in payload.get("observations", []):
        observation_date = observation.get("date", "")
        for column, value in observation.items():
            if not column.startswith(prefix) or value in {"", "."}:
                continue
            compact_vintage = column.removeprefix(prefix)
            if len(compact_vintage) != 8 or not compact_vintage.isdigit():
                continue
            vintage_date = f"{compact_vintage[:4]}-{compact_vintage[4:6]}-{compact_vintage[6:]}"
            rows.append({
                "series_id": series_id,
                "control": meta["control"],
                "frequency": meta["frequency"],
                "transform": meta["transform"],
                "observation_date": observation_date,
                "value": value,
                "vintage_date": vintage_date,
                "release_timestamp": vintage_date,
                "release_time_precision": "date_only_from_alfred",
                "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            })
    return rows


def expand_point_in_time(series_id: str, payload: dict, meta: dict, cutoff: str) -> list[dict[str, str]]:
    """Normalize a one-cutoff API response to the same long schema."""
    rows = []
    for observation in payload.get("observations", []):
        value = observation.get("value", "")
        if value in {"", "."}:
            continue
        rows.append({
            "series_id": series_id,
            "control": meta["control"],
            "frequency": meta["frequency"],
            "transform": meta["transform"],
            "observation_date": observation.get("date", ""),
            "value": value,
            "vintage_date": cutoff,
            "release_timestamp": cutoff,
            "release_time_precision": "date_only_from_alfred_point_in_time_query",
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
        })
    return rows


def as_of_series(frame: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    eligible = frame.loc[frame["vintage_date"] <= cutoff].sort_values(["observation_date", "vintage_date"])
    return eligible.groupby("observation_date", as_index=False).tail(1).sort_values("observation_date")


def latest_value(frame: pd.DataFrame, cutoff: pd.Timestamp) -> tuple[float | None, pd.Timestamp | None, pd.Timestamp | None]:
    snapshot = as_of_series(frame, cutoff)
    if snapshot.empty:
        return None, None, None
    row = snapshot.iloc[-1]
    return float(row.value), pd.Timestamp(row.observation_date), pd.Timestamp(row.vintage_date)


def snapshot_dates(start: str, end: str) -> pd.DatetimeIndex:
    """Month-end cutoffs plus a non-month-end final as-of date, if requested."""
    end_date = pd.Timestamp(end).normalize()
    dates = pd.date_range(pd.Timestamp(start).to_period("M").to_timestamp("M"), end_date.to_period("M").to_timestamp("M"), freq="ME")
    if end_date != end_date + pd.offsets.MonthEnd(0):
        dates = dates[dates < end_date].append(pd.DatetimeIndex([end_date]))
    return dates


def build_snapshot_panel(frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    dates = snapshot_dates(start, end)
    by_series = {series: group.assign(observation_date=pd.to_datetime(group.observation_date), vintage_date=pd.to_datetime(group.vintage_date), value=pd.to_numeric(group.value)) for series, group in frame.groupby("series_id")}
    rows = []
    for cutoff in dates:
        row: dict[str, object] = {"information_cutoff": cutoff.date().isoformat()}
        for series_id, meta in SERIES.items():
            group = by_series.get(series_id)
            if group is None:
                continue
            value, observation, vintage = latest_value(group, cutoff)
            key = meta["control"]
            row[key] = value
            row[f"{key}_observation_date"] = None if observation is None else observation.date().isoformat()
            row[f"{key}_vintage_date"] = None if vintage is None else vintage.date().isoformat()
        # Derived measures must use values selected from the same information set.
        pce = by_series.get("PCEPI")
        if pce is not None:
            selected = as_of_series(pce, cutoff)
            if not selected.empty:
                base = selected.loc[selected.observation_date.eq(pd.Timestamp("2010-01-01"))]
                latest = selected.iloc[-1]
                if not base.empty:
                    row["pce_cumulative_since_2010"] = 100 * (float(latest.value) / float(base.iloc[-1].value) - 1)
        income = by_series.get("DSPIC96")
        if income is not None:
            selected = as_of_series(income, cutoff)
            if not selected.empty:
                latest = selected.iloc[-1]
                prior = selected.loc[selected.observation_date.eq(latest.observation_date - pd.DateOffset(months=12))]
                if not prior.empty:
                    row["real_disposable_income_yoy"] = 100 * (float(latest.value) / float(prior.iloc[-1].value) - 1)
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end", default=datetime.now(ZoneInfo("America/New_York")).date().isoformat())
    parser.add_argument("--series", nargs="*", choices=sorted(SERIES), help="Optional series IDs to collect.")
    args = parser.parse_args()
    key = read_key()
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    if LONG_OUT.exists():
        existing = pd.read_csv(LONG_OUT, dtype=str).fillna("").to_dict("records")
    else:
        existing = []
    rows: list[dict[str, str]] = []
    previous_manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    statuses = dict(previous_manifest.get("series", {}))
    requested = args.series or list(SERIES)
    for series_id in requested:
        meta = SERIES[series_id]
        if series_id in POINT_IN_TIME_SERIES:
            try:
                expanded = []
                raw_files = []
                digests = []
                unavailable_cutoffs = []
                for cutoff in snapshot_dates(args.start, args.end):
                    cutoff_text = cutoff.date().isoformat()
                    first_available = POINT_IN_TIME_FIRST_AVAILABLE.get(series_id)
                    if first_available is not None and cutoff < first_available:
                        unavailable_cutoffs.append({"cutoff": cutoff_text, "reason": "before_first_alfred_release"})
                        continue
                    raw_file = RAW / f"{series_id}_as_of_{cutoff_text}.json"
                    try:
                        fetched = False
                        if raw_file.exists():
                            body = raw_file.read_bytes()
                            payload = json.loads(body)
                        else:
                            for attempt in range(5):
                                try:
                                    payload, body = request_point_in_time(series_id, cutoff_text, args.start, key)
                                    fetched = True
                                    break
                                except HTTPError as exc:
                                    if exc.code != 429 or attempt == 4:
                                        raise
                                    time.sleep(2 ** attempt)
                    except HTTPError as exc:
                        # The monthly series' ALFRED release history starts in
                        # 2013. Preserve the later eligible snapshots instead
                        # of discarding an otherwise valid archive.
                        unavailable_cutoffs.append({"cutoff": cutoff_text, "http_status": exc.code})
                        continue
                    raw_file.write_bytes(body)
                    raw_files.append(str(raw_file.relative_to(ROOT)))
                    digests.append(hashlib.sha256(body).hexdigest())
                    expanded.extend(expand_point_in_time(series_id, payload, meta, cutoff_text))
                    # FRED's public API enforces rate limits. This keeps the
                    # 161 post-release monthly requests below 100/minute.
                    if fetched:
                        time.sleep(0.65)
                rows.extend(expanded)
                if not expanded:
                    raise RuntimeError("No usable ALFRED point-in-time observations were returned.")
                statuses.pop("USEPUINDXD", None)
                statuses[series_id] = {
                    "status": "archived_from_alfred_point_in_time", "records": len(expanded),
                    "raw_files": raw_files, "sha256": digests,
                    "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
                    "timestamp_precision": "date_only_from_alfred",
                    "method": "One FRED observations API request per configured information cutoff; realtime_start=realtime_end=cutoff.",
                    "requested_cutoffs": int(len(snapshot_dates(args.start, args.end))),
                    "collected_cutoffs": int(len(raw_files)),
                    "unavailable_cutoffs": unavailable_cutoffs,
                }
            except Exception as exc:
                statuses[series_id] = {"status": "collection_failed", "message": str(exc)}
            continue
        try:
            payload, body = request_full_vintage_history(series_id, args.start, args.end, key)
            responses = [(args.start, args.end, payload, body)]
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            if "exceeds the maximum number of vintage dates" not in error_body:
                statuses[series_id] = {
                    "status": "primary_release_archive_required", "http_status": exc.code,
                    "message": "ALFRED does not expose this series' vintage history; collect dated primary releases rather than current revised FRED values.",
                    "api_message": error_body[:500],
                    "primary_source": "BLS Employment Situation archives" if series_id == "U6RATE" else "Publisher release archive or licensed source",
                }
                continue
            responses = []
            blocked_by_primary_archive = False
            windows = annual_windows(args.start, args.end)
            for window_start, window_end in windows:
                try:
                    payload, body = request_full_vintage_history(series_id, window_start, window_end, key)
                    responses.append((window_start, window_end, payload, body))
                except HTTPError as yearly_error:
                    yearly_body = yearly_error.read().decode("utf-8", errors="replace")
                    if "exceeds the maximum number of vintage dates" not in yearly_body:
                        statuses[series_id] = {
                            "status": "primary_release_archive_required", "http_status": yearly_error.code,
                            "message": "ALFRED does not expose this series' vintage history; collect dated primary releases rather than current revised FRED values.",
                            "api_message": yearly_body[:500], "primary_source": "Publisher release archive or licensed source",
                        }
                        blocked_by_primary_archive = True
                        break
                    # Some publisher series have daily change markers. Monthly
                    # chunks keep those series below ALFRED's response cap.
                    for month_start, month_end in monthly_windows(window_start, window_end):
                        try:
                            payload, body = request_full_vintage_history(series_id, month_start, month_end, key)
                            responses.append((month_start, month_end, payload, body))
                        except HTTPError as monthly_error:
                            monthly_body = monthly_error.read().decode("utf-8", errors="replace")
                            statuses[series_id] = {
                                "status": "primary_release_archive_required", "http_status": monthly_error.code,
                                "message": "ALFRED does not expose this series' vintage history; collect dated primary releases rather than current revised FRED values.",
                                "api_message": monthly_body[:500], "primary_source": "Publisher release archive or licensed source",
                            }
                            blocked_by_primary_archive = True
                            break
                if blocked_by_primary_archive:
                    break
            if blocked_by_primary_archive:
                continue
        try:
            expanded = []
            raw_files = []
            digests = []
            for window_start, window_end, payload, body in responses:
                raw_file = RAW / f"{series_id}_{window_start}_{window_end}_output_type_2.json"
                raw_file.write_bytes(body)
                raw_files.append(str(raw_file.relative_to(ROOT)))
                digests.append(hashlib.sha256(body).hexdigest())
                expanded.extend(expand_output_type_2(series_id, payload, meta))
            # A boundary vintage can occur in adjacent response windows.
            expanded = list({(r["series_id"], r["observation_date"], r["vintage_date"]): r for r in expanded}.values())
            rows.extend(expanded)
            statuses[series_id] = {
                "status": "archived_from_alfred", "records": len(expanded),
                "raw_files": raw_files, "sha256": digests,
                "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
                "timestamp_precision": "date_only_from_alfred",
            }
        except Exception as exc:
            statuses[series_id] = {"status": "collection_failed", "message": str(exc)}
    fieldnames = ["series_id", "control", "frequency", "transform", "observation_date", "value", "vintage_date", "release_timestamp", "release_time_precision", "source_url"]
    # Preserve already-collected controls during a targeted refresh, replacing
    # only the series explicitly requested on this run.
    retained = [row for row in existing if row.get("series_id") not in requested]
    combined_rows = retained + rows
    with LONG_OUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(sorted(combined_rows, key=lambda r: (r["series_id"], r["observation_date"], r["vintage_date"])))
    long = pd.DataFrame(combined_rows)
    if long.empty:
        snapshot = pd.DataFrame(columns=["information_cutoff"])
    else:
        snapshot = build_snapshot_panel(long, args.start, args.end)
    snapshot.to_csv(SNAPSHOT_OUT, index=False)
    manifest = {
        "built_at_utc": datetime.now(ZoneInfo("UTC")).replace(microsecond=0).isoformat(),
        "method": "ALFRED series/observations output_type=2, except USEPUINDXM which uses one point-in-time request per information cutoff; all reported values retain their observation and vintage date.",
        "coverage": {"start": args.start, "end": args.end},
        "api_key_written": False,
        "series": statuses,
        "outputs": {"long_observations": str(LONG_OUT.relative_to(ROOT)), "as_of_snapshots": str(SNAPSHOT_OUT.relative_to(ROOT))},
        "limitation": "ALFRED vintage dates are dates, not intraday timestamps. Series without ALFRED history are explicitly blocked pending primary-release archives.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"rows_added": len(rows), "rows_total": len(combined_rows), "snapshot_rows": len(snapshot), "series": {k: v["status"] for k, v in statuses.items()}}, indent=2))


if __name__ == "__main__":
    main()
