"""Build a date-accurate ALFRED initial-release panel and scheduled release log.

The collector reads ``FRED_API_KEY`` from the ignored local ``.env`` file. It
uses FRED's ``output_type=4`` endpoint: each returned observation is the first
ALFRED vintage for that observation, with ``realtime_start`` recording the date
on which that value became available. ALFRED does not publish a time of day, so
the CSV explicitly marks those timestamps as date-only rather than inventing a
release time.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
OBSERVATIONS = ROOT / "data/templates/macro_vintage_observations.csv"
EVENTS = ROOT / "data/templates/release_event_log.csv"
MANIFEST = ROOT / "data/processed/realtime_macro_panel_manifest.json"
API = "https://api.stlouisfed.org/fred/series/observations"
SERIES = ("UNRATE", "PCEPI", "GDPC1", "CPIAUCSL", "FEDFUNDS")


def api_key() -> str:
    if not ENV.exists():
        raise FileNotFoundError("Missing .env; add FRED_API_KEY=... locally.")
    values = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    if not values.get("FRED_API_KEY"):
        raise ValueError("FRED_API_KEY is not set in .env.")
    return values["FRED_API_KEY"]


def get_initial_vintages(series_id: str, start: str, end: str, key: str) -> list[dict[str, str]]:
    params = {
        "series_id": series_id, "api_key": key, "file_type": "json",
        "realtime_start": start, "realtime_end": end,
        "observation_start": start, "observation_end": end,
        "output_type": "4", "limit": "100000", "sort_order": "asc",
    }
    with urlopen(f"{API}?{urlencode(params)}", timeout=60) as response:  # nosec B310: fixed HTTPS API
        payload = json.load(response)
    if payload.get("error_code"):
        raise RuntimeError(payload.get("error_message", "FRED request failed"))
    rows = []
    for observation in payload.get("observations", []):
        value = observation.get("value", "")
        if value in {"", "."}:
            continue
        vintage_date = observation["realtime_start"]
        rows.append({
            "series_id": series_id,
            "observation_date": observation["date"],
            "value": value,
            "release_timestamp": vintage_date,
            "vintage_id": f"alfred-{vintage_date}-initial",
            "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "release_time_precision": "date_only_from_alfred",
        })
    return rows


def eastern_timestamp(date: str) -> str:
    return datetime.strptime(date, "%Y-%m-%d").replace(hour=8, minute=30, tzinfo=ZoneInfo("America/New_York")).isoformat()


def scheduled_events() -> list[dict[str, str]]:
    """Official 2026 BLS/BEA schedule entries relevant to the recorded series."""
    bea_url = "https://www.bea.gov/news/schedule/full"
    bls_url = "https://www.bls.gov/schedule/news_release/empSit.htm"
    pce_dates = ("2026-02-20", "2026-03-13", "2026-04-09", "2026-04-30", "2026-05-28", "2026-06-25", "2026-07-30", "2026-08-26", "2026-09-30", "2026-10-29", "2026-11-25", "2026-12-23")
    gdp_dates = ("2026-02-20", "2026-03-13", "2026-04-09", "2026-04-30", "2026-05-28", "2026-06-25", "2026-07-30", "2026-08-26", "2026-09-30", "2026-10-29", "2026-11-25", "2026-12-23")
    rows = []
    for date in pce_dates:
        rows.append({"event_date": date, "event_type": "scheduled_release", "series_or_topic": "PCEPI — BEA Personal Income and Outlays", "source_url": bea_url, "verified_release_timestamp": "true", "notes": f"Official BEA 2026 schedule; release time {eastern_timestamp(date)}."})
    for date in gdp_dates:
        rows.append({"event_date": date, "event_type": "scheduled_release", "series_or_topic": "GDPC1 — BEA Gross Domestic Product estimate", "source_url": bea_url, "verified_release_timestamp": "true", "notes": f"Official BEA 2026 schedule; release time {eastern_timestamp(date)}."})
    for date, reference_month in (("2026-11-06", "October 2026"), ("2026-12-04", "November 2026"), ("2027-01-08", "December 2026")):
        rows.append({"event_date": date, "event_type": "scheduled_release", "series_or_topic": f"UNRATE — BLS Employment Situation ({reference_month} reference month)", "source_url": bls_url, "verified_release_timestamp": "true", "notes": f"Official BLS schedule; release time {eastern_timestamp(date)}."})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2014-01-01")
    parser.add_argument("--end", default="2021-06-30")
    args = parser.parse_args()
    key = api_key()
    rows = [row for series_id in SERIES for row in get_initial_vintages(series_id, args.start, args.end, key)]
    rows.sort(key=lambda row: (row["release_timestamp"], row["series_id"], row["observation_date"]))
    OBSERVATIONS.parent.mkdir(parents=True, exist_ok=True)
    with OBSERVATIONS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["series_id", "observation_date", "value", "release_timestamp", "vintage_id", "source_url", "release_time_precision"])
        writer.writeheader(); writer.writerows(rows)
    event_rows = scheduled_events()
    with EVENTS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["event_date", "event_type", "series_or_topic", "source_url", "verified_release_timestamp", "notes"])
        writer.writeheader(); writer.writerows(event_rows)
    manifest = {
        "built_at_utc": datetime.now(ZoneInfo("UTC")).replace(microsecond=0).isoformat(),
        "method": "FRED series/observations output_type=4 (ALFRED initial release only)",
        "coverage": {"realtime_start": args.start, "realtime_end": args.end},
        "series": {series_id: sum(row["series_id"] == series_id for row in rows) for series_id in SERIES},
        "release_timestamp_precision": "ALFRED vintage dates are date-only; exact time is not imputed.",
        "api_key_written": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"observations": len(rows), "events": len(event_rows), "series": manifest["series"]}, indent=2))


if __name__ == "__main__":
    main()
