"""Create a bounded, source-panel-based plan and coded-item template for history."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "data" / "corpus" / "historical"
PANEL = HISTORICAL / "source_panel.csv"
PLAN = HISTORICAL / "collection_plan.csv"
TEMPLATE = HISTORICAL / "raw" / "historical_items_template.csv"
MANIFEST = HISTORICAL / "collection_manifest.json"
ITEM_FIELDS = [
    "item_id", "published_at", "available_on", "source_domain", "source_stratum",
    "include_default", "is_duplicate", "suspected_automated", "tone", "frame_price_level",
    "salience_recession_risk", "factual_calibration", "url", "publisher_url", "text",
    "text_representation", "archive_source", "archive_record_id", "retrieved_at",
    "extraction_method", "license_or_terms_note",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2020-01")
    parser.add_argument("--end", default="2025-12")
    args = parser.parse_args()
    start, end = pd.Period(args.start, freq="M"), pd.Period(args.end, freq="M")
    if end < start:
        raise ValueError("--end must not precede --start")
    with PANEL.open(encoding="utf-8", newline="") as stream:
        panel = list(csv.DictReader(stream))
    enabled = [row for row in panel if row["collection_enabled"].strip().casefold() == "true"]
    months = pd.period_range(start, end, freq="M")
    plan = [
        {
            "month": str(month), "source_domain": source["source_domain"], "source_stratum": source["source_stratum"],
            "collection_method": source["collection_method"], "query_status": "not_started",
            "candidate_count": "", "accepted_count": "", "notes": "Record Common Crawl index/crawl ID and query parameters at collection time.",
        }
        for month in months for source in enabled
    ]
    with PLAN.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(plan[0]))
        writer.writeheader()
        writer.writerows(plan)
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    with TEMPLATE.open("w", encoding="utf-8", newline="") as stream:
        csv.DictWriter(stream, fieldnames=ITEM_FIELDS).writeheader()
    manifest = {
        "created_at": datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat(),
        "target_months": len(months), "start": str(start), "end": str(end),
        "enabled_sources": len(enabled), "enabled_by_stratum": {stratum: sum(row["source_stratum"] == stratum for row in enabled) for stratum in sorted({row["source_stratum"] for row in panel})},
        "social_coverage": "Not collected: no lawful, configured public historical archive. Preserve this missingness rather than imputing zero.",
        "source_panel": str(PANEL), "plan": str(PLAN), "coded_item_template": str(TEMPLATE),
        "next_step": "Collect only records permitted by each source/archive, retain raw archive IDs and availability timestamps, code the records, then save reviewed rows as raw/historical_items.csv before aggregation.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
