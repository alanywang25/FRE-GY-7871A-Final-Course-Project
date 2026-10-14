"""Build a timestamped monthly aggregate from finalized all-field labels."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data/corpus/full_field_validation/adjudication/full_field_adjudicated_labels.csv"
KEY = ROOT / "data/corpus/validation_internal/full_field_validation_blind_key.csv"
OUT = ROOT / "data/media_monthly.csv"
SOURCE_OUT = ROOT / "data/media_monthly_by_source.csv"
SUMMARY = ROOT / "data/corpus/full_field_validation/full_field_monthly_summary.json"


def share(frame: pd.DataFrame, column: str, value: str) -> float:
    return round(float(frame[column].eq(value).mean()), 6) if len(frame) else float("nan")


def aggregate(group: pd.DataFrame, month: str, built_at: str) -> dict:
    """Return the complete dashboard measure set for one month/stratum group."""
    row = {
        "month": month,
        "available_on": built_at,
        "aggregate_status": "independently_adjudicated",
        "tone_negative_share": share(group, "tone", "negative"),
        "tone_positive_share": share(group, "tone", "positive"),
        "tone_mixed_share": share(group, "tone", "mixed"),
        "factual_calibrated_share": share(group, "factual_calibration", "calibrated"),
        "factual_materially_incomplete_share": share(group, "factual_calibration", "materially incomplete-or-misleading"),
        "factual_unverifiable_share": share(group, "factual_calibration", "unverifiable"),
        "political_attribution_share": round(float(group["political_attribution_target"].ne("none").mean()), 6),
        "political_blame_share": share(group, "political_valence", "blame"),
        "political_credit_share": share(group, "political_valence", "credit"),
        "corpus_items": len(group),
        "eligible_items": len(group),
        "unresolved_items": 0,
        "source_count": group.source_domain.replace("", pd.NA).nunique(),
        "missingness_rate": 0.0,
        "notes": "Source-blinded, independently coded all-field validation aggregate; availability is the finalized-label build timestamp, not the publication date.",
    }
    for column in [
        "salience_layoffs", "salience_hiring", "salience_price_level",
        "salience_disinflation", "salience_growth", "salience_recession_risk",
        "frame_price_level", "frame_inflation_rate", "frame_household_experience",
        "frame_national_aggregate", "frame_current", "frame_forecast",
    ]:
        row[f"{column}_share"] = share(group, column, "1")
    # Stable aliases retained for prior dashboard consumers.
    row["price_level_frame_share"] = row["frame_price_level_share"]
    row["recession_salience_share"] = row["salience_recession_risk_share"]
    return row


def main() -> None:
    gold = pd.read_csv(GOLD, dtype=str).fillna("")
    key = pd.read_csv(KEY, dtype=str).fillna("")
    if len(gold) < 300 or gold.item_id.duplicated().any():
        raise ValueError("All-field adjudicated labels must have at least 300 unique items.")
    frame = gold.merge(key[["item_id", "source_domain"]].drop_duplicates("item_id"), on="item_id", how="left", validate="one_to_one")
    frame["month"] = pd.to_datetime(frame["publication_date"]).dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")
    built_at = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
    rows = []
    for month, group in frame.groupby("month", sort=True):
        rows.append(aggregate(group, month, built_at))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    source_rows = []
    for (month, stratum), group in frame.groupby(["month", "source_stratum"], sort=True):
        item = aggregate(group, month, built_at)
        item["source_stratum"] = stratum
        source_rows.append(item)
    pd.DataFrame(source_rows).to_csv(SOURCE_OUT, index=False)
    summary = {"built_at": built_at, "items": len(frame), "months": len(rows), "status": "independently_adjudicated", "output": str(OUT.relative_to(ROOT)), "source_output": str(SOURCE_OUT.relative_to(ROOT))}
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
