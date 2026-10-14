"""Add compact archive citations to completed historical annotation packets."""
from __future__ import annotations
import argparse, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "data/corpus/historical/independent_validation"
KEY = ROOT / "data/corpus/historical/validation_internal/historical_validation_blind_key.csv"
RAW = ROOT / "data/corpus/historical/raw/historical_items.csv"

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--packet", type=Path, default=PACKETS / "annotator_a.csv")
    args = parser.parse_args()
    key = {row["blind_id"]: row for row in csv.DictReader(KEY.open(encoding="utf-8", newline=""))}
    raw = {row["item_id"]: row for row in csv.DictReader(RAW.open(encoding="utf-8", newline=""))}
    with args.packet.open(encoding="utf-8", newline="") as stream: rows = list(csv.DictReader(stream)); fields = stream.seek(0) or csv.DictReader(args.packet.open(encoding="utf-8", newline="")).fieldnames
    changed = 0
    for row in rows:
        if not row.get("label_provenance", "").strip().startswith("human_") or row.get("benchmark_reference", "").strip(): continue
        source = raw[key[row["blind_id"]]["item_id"]]
        date = source["published_at"][:10]
        status = row.get("factual_calibration", "").strip() or "unverifiable"
        row["benchmark_reference"] = f"Independent historical review — {status}; Internet Archive TV News caption record, {source['source_domain']}, aired {date}; record {source['archive_record_id']}."
        changed += 1
    with args.packet.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    print(f"Filled {changed} benchmark references in {args.packet}")

if __name__ == "__main__": main()
