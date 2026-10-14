"""Validate and aggregate an availability-dated historical media archive.

The input is deliberately a coded, item-level file.  This script does not
scrape, infer, or backfill labels: it turns a documented archive into the same
monthly schema consumed by the dashboard once the archive has been reviewed.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "corpus" / "historical" / "raw" / "historical_items.csv"
DEFAULT_OUTPUT = ROOT / "data" / "corpus" / "historical" / "processed" / "historical_media_monthly.csv"
DEFAULT_STATUS = ROOT / "data" / "corpus" / "historical" / "processed" / "historical_series_status.json"
LABEL_VALIDATION = ROOT / "data" / "corpus" / "historical" / "validation" / "historical_label_validation_summary.json"
ADJUDICATION = ROOT / "data" / "corpus" / "historical" / "independent_validation" / "adjudication" / "historical_tone_adjudication_summary.json"
VALIDATION_KEY = ROOT / "data" / "corpus" / "historical" / "validation_internal" / "historical_validation_blind_key.csv"
EXTENSION_LABEL_VALIDATION = ROOT / "data" / "corpus" / "historical" / "validation" / "historical_extension_label_validation_summary.json"
EXTENSION_ADJUDICATION = ROOT / "data" / "corpus" / "historical" / "supplemental_validation" / "adjudication" / "extension_tone_adjudication_summary.json"
EXTENSION_VALIDATION_KEY = ROOT / "data" / "corpus" / "historical" / "validation_internal" / "historical_extension_blind_key.csv"
REQUIRED = {
    "item_id", "published_at", "available_on", "source_domain", "source_stratum",
    "include_default", "is_duplicate", "suspected_automated", "tone",
    "frame_price_level", "salience_recession_risk", "factual_calibration",
}
METRICS = [
    "tone_negative_share", "tone_positive_share", "tone_mixed_share",
    "price_level_frame_share", "recession_salience_share", "factual_calibrated_share",
    "factual_materially_incomplete_share",
]


def truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.casefold().eq("true")


def month_end(value: pd.Timestamp) -> pd.Timestamp:
    """Convert a UTC item timestamp to the naive monthly index used below."""
    return value.tz_localize(None).to_period("M").to_timestamp("M")


def independent_validation_complete(first_month: pd.Timestamp | None, last_month: pd.Timestamp | None) -> tuple[bool, str]:
    if not LABEL_VALIDATION.exists() or not ADJUDICATION.exists() or not VALIDATION_KEY.exists():
        return False, "Independent-label validation artifacts are incomplete."
    try:
        labels = json.loads(LABEL_VALIDATION.read_text(encoding="utf-8"))
        adjudication = json.loads(ADJUDICATION.read_text(encoding="utf-8"))
        if not (bool(labels.get("gate_passed")) and bool(adjudication.get("ready"))):
            return False, "Independent-label validation or tone adjudication is incomplete."
        key = pd.read_csv(VALIDATION_KEY, parse_dates=["published_at"])
        original_first = month_end(key["published_at"].min()) if not key.empty else None
        original_last = month_end(key["published_at"].max()) if not key.empty else None
        needs_extension = first_month is not None and (original_first is None or first_month < original_first)
        if needs_extension:
            if not (EXTENSION_LABEL_VALIDATION.exists() and EXTENSION_ADJUDICATION.exists() and EXTENSION_VALIDATION_KEY.exists()):
                return False, "Historical archive extends beyond the independently labeled sample; create the supplemental blinded validation packet."
            extension_labels = json.loads(EXTENSION_LABEL_VALIDATION.read_text(encoding="utf-8"))
            extension_adjudication = json.loads(EXTENSION_ADJUDICATION.read_text(encoding="utf-8"))
            extension_key = pd.read_csv(EXTENSION_VALIDATION_KEY, parse_dates=["published_at"])
            extension_first = month_end(extension_key["published_at"].min()) if not extension_key.empty else None
            extension_last = month_end(extension_key["published_at"].max()) if not extension_key.empty else None
            if not (bool(extension_labels.get("gate_passed")) and bool(extension_adjudication.get("ready"))):
                return False, "Supplemental extension independent labeling or tone adjudication is incomplete."
            if extension_first is None or extension_last is None or extension_first > first_month:
                return False, "Supplemental validation does not cover the first month of the historical extension."
        if last_month is not None and original_last is not None and last_month > original_last:
            return False, "Historical archive extends beyond the independently labeled sample; create and complete a supplemental blinded validation packet."
        return (
            True,
            "Independent-label validation and tone adjudication are complete for the original and supplemental historical samples."
            if needs_extension else "Independent-label validation and tone adjudication are complete.",
        )
    except json.JSONDecodeError:
        return False, "Historical validation artifacts could not be read."


def build(input_path: Path, output_path: Path, status_path: Path, min_history_months: int) -> dict:
    built_at = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    if not input_path.exists():
        status = {
            "built_at": built_at, "ready": False, "input_exists": False,
            "message": "No historical archive found. Supply the documented coded input; no series was fabricated.",
            "expected_input": str(input_path), "minimum_history_months": min_history_months,
        }
        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
        return status

    raw = pd.read_csv(input_path, dtype=str).fillna("")
    missing = sorted(REQUIRED - set(raw.columns))
    if missing:
        status = {"built_at": built_at, "ready": False, "input_exists": True,
                  "message": "Historical archive is missing required fields.", "missing_columns": missing}
        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
        return status

    for column in ("published_at", "available_on"):
        raw[column] = pd.to_datetime(raw[column], errors="coerce", utc=True)
    invalid_dates = int(raw[["published_at", "available_on"]].isna().any(axis=1).sum())
    usable = raw.dropna(subset=["published_at", "available_on"]).copy()
    usable["month"] = usable["published_at"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp("M")
    included = truthy(usable["include_default"]) & ~truthy(usable["is_duplicate"]) & ~truthy(usable["suspected_automated"])
    coded = usable.loc[included].drop_duplicates("item_id", keep="first").copy()
    eligible = usable.loc[included].groupby("month").size().rename("eligible_items")
    grouped = coded.groupby("month", dropna=False)
    result = pd.DataFrame(index=eligible.index).sort_index()
    result["available_on"] = grouped["available_on"].max().reindex(result.index)
    first_month = result.index.min() if len(result) else None
    last_month = result.index.max() if len(result) else None
    validation_complete, validation_message = independent_validation_complete(first_month, last_month)
    result["aggregate_status"] = (
        "historical_coded_independent_validation_complete"
        if validation_complete else "historical_coded_pending_independent_validation"
    )
    result["tone_negative_share"] = grouped["tone"].apply(lambda s: (s == "negative").mean()).reindex(result.index)
    result["tone_positive_share"] = grouped["tone"].apply(lambda s: (s == "positive").mean()).reindex(result.index)
    result["tone_mixed_share"] = grouped["tone"].apply(lambda s: (s == "mixed").mean()).reindex(result.index)
    result["price_level_frame_share"] = grouped["frame_price_level"].apply(lambda s: (s == "1").mean()).reindex(result.index)
    result["recession_salience_share"] = grouped["salience_recession_risk"].apply(lambda s: (s == "1").mean()).reindex(result.index)
    result["factual_calibrated_share"] = grouped["factual_calibration"].apply(lambda s: (s == "calibrated").mean()).reindex(result.index)
    result["factual_materially_incomplete_share"] = grouped["factual_calibration"].apply(lambda s: (s == "materially incomplete-or-misleading").mean()).reindex(result.index)
    result["corpus_items"] = grouped.size().reindex(result.index, fill_value=0).astype(int)
    result["eligible_items"] = eligible.reindex(result.index, fill_value=0).astype(int)
    result["unresolved_items"] = result["eligible_items"] - result["corpus_items"]
    result["source_count"] = grouped["source_domain"].nunique().reindex(result.index, fill_value=0).astype(int)
    result["missingness_rate"] = 1 - result["corpus_items"].div(result["eligible_items"].replace(0, pd.NA))
    result["notes"] = (
        "Historical coded archive; availability is the latest item-level availability timestamp in the month. "
        + (validation_message if validation_complete else validation_message + " Do not model this series yet.")
    )
    result = result.reset_index()
    result["month"] = result["month"].dt.strftime("%Y-%m-%d")
    result["available_on"] = pd.to_datetime(result["available_on"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    result[METRICS + ["missingness_rate"]] = result[METRICS + ["missingness_rate"]].round(6)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)

    months = len(result)
    span = {"first_month": result["month"].min() if months else None, "last_month": result["month"].max() if months else None}
    status = {
        "built_at": built_at, "ready": months >= min_history_months, "input_exists": True,
        "message": (
            "Historical series is ready for downstream modeling; finalized-label classifier results remain a development-set diagnostic."
            if months >= min_history_months and validation_complete
            else "Historical series built; it remains ineligible for effect estimation until independent-label validation passes."
            if months >= min_history_months
            else "Historical series built but is shorter than the required pre-prediction history."
        ),
        "input_rows": int(len(raw)), "included_unique_items": int(len(coded)), "invalid_date_rows": invalid_dates,
        "independent_validation_complete": validation_complete,
        "independent_validation_message": validation_message,
        "monthly_rows": months, "minimum_history_months": min_history_months, "coverage": span,
        "output": str(output_path),
    }
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--min-history-months", type=int, default=60)
    args = parser.parse_args()
    print(json.dumps(build(args.input, args.output, args.status, args.min_history_months), indent=2))


if __name__ == "__main__":
    main()
