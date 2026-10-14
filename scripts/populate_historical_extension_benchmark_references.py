"""Synchronize compact archive references to manual extension-packet reviews.

Only ``benchmark_reference`` is changed for keyed, human-reviewed records.
The reader accepts UTF-8 and the Windows-1252 export commonly produced by
spreadsheet applications, then writes a standards-compliant UTF-8 CSV.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "data/corpus/historical/supplemental_validation"
KEY = ROOT / "data/corpus/historical/validation_internal/historical_extension_blind_key.csv"
RAW = ROOT / "data/corpus/historical/raw/historical_items.csv"
AUDIT = PACKETS / "benchmark_reference_update_audit.json"


def read_rows(path: Path) -> tuple[list[str], list[list[str]], str]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                rows = list(csv.reader(stream))
            return rows[0], rows[1:], encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path}")


def main() -> None:
    with KEY.open(encoding="utf-8", newline="") as stream:
        item_for_blind_id = {row["blind_id"]: row["item_id"] for row in csv.DictReader(stream)}
    with RAW.open(encoding="utf-8", newline="") as stream:
        source_for_item = {row["item_id"]: row for row in csv.DictReader(stream)}

    audit: dict[str, object] = {"packets": {}}
    for filename in ("annotator_a.csv", "annotator_b.csv"):
        path = PACKETS / filename
        fields, rows, input_encoding = read_rows(path)
        positions = {field: number for number, field in enumerate(fields)}
        required = {"blind_id", "factual_calibration", "benchmark_reference", "label_provenance"}
        if missing := required - set(positions):
            raise ValueError(f"{path} is missing required columns: {sorted(missing)}")
        updated = 0
        for row in rows:
            if len(row) <= max(positions.values()):
                continue
            blind_id = row[positions["blind_id"]].strip()
            provenance = row[positions["label_provenance"]].strip()
            if blind_id not in item_for_blind_id or not provenance.startswith("human_"):
                continue
            source = source_for_item[item_for_blind_id[blind_id]]
            status = row[positions["factual_calibration"]].strip() or "unverifiable"
            date = source["published_at"][:10]
            row[positions["benchmark_reference"]] = (
                f"Independent historical review — {status}; Internet Archive TV News caption record, "
                f"{source['source_domain']}, aired {date}; record {source['archive_record_id']}."
            )
            updated += 1
        with path.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerows([fields, *rows])
        audit["packets"][filename] = {
            "input_encoding": input_encoding,
            "rows_updated": updated,
            "nonstandard_width_rows_preserved": sum(len(row) != len(fields) for row in rows),
        }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
