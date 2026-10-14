"""Clear annotator notes without changing labels or provenance."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKETS = [
    ROOT / "data" / "corpus" / "labeling" / "annotator_a.csv",
    ROOT / "data" / "corpus" / "labeling" / "annotator_b.csv",
]


for packet in PACKETS:
    with packet.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    for row in rows:
        row["annotator_notes"] = ""
    with packet.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Cleared annotator_notes: {packet.name} ({len(rows)} rows)")
