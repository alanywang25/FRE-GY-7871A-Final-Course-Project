"""Create a lean, balanced, contiguous TV-caption backfill plan."""
from __future__ import annotations
import csv
import argparse
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "data" / "corpus" / "historical"
PANEL = HIST / "tvnews_source_panel.csv"
OUT = HIST / "tvnews_backfill_collection_plan.csv"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-07")
    parser.add_argument("--end", default="2019-12")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    panel = list(csv.DictReader(PANEL.open(encoding="utf-8", newline="")))
    national = [row for row in panel if row["source_stratum"] == "national"]
    local = [row for row in panel if row["source_stratum"] == "local"]
    rows = []
    months = pd.period_range(args.start, args.end, freq="M")
    if not len(months):
        raise ValueError("The requested historical range is empty.")
    for index, month in enumerate(months):
        for source in (national[index % len(national)], local[index % len(local)]):
            rows.append({"month": str(month), "source_domain": source["source_domain"], "archive_contributor": source["archive_contributor"], "source_stratum": source["source_stratum"], "query_status": "not_started", "candidate_count": "", "accepted_count": "", "notes": "Rotating balanced national/local backfill; one coded caption record per source-month when available."})
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(f"Created {len(rows)} tasks at {args.output}")

if __name__ == "__main__": main()
