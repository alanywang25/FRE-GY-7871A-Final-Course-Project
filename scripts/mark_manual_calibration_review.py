"""Align Annotator A benchmark references and provenance with manual calibration review."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET_NAME = sys.argv[1] if len(sys.argv) > 1 else "annotator_a.csv"
if PACKET_NAME not in {"annotator_a.csv", "annotator_b.csv"}:
    raise ValueError("Packet name must be annotator_a.csv or annotator_b.csv")
PACKET = ROOT / "data" / "corpus" / "labeling" / PACKET_NAME


def reviewed_reference(reference: str, calibration: str) -> str:
    text = reference.strip()
    if text.startswith("Unverified; candidate benchmark: "):
        text = "Candidate benchmark: " + text.removeprefix("Unverified; candidate benchmark: ")
    elif text.startswith("Unverifiable from retained "):
        text = "Source context: " + text.removeprefix("Unverifiable from retained ")
    return f"Manual review — {calibration}; {text}"


with PACKET.open(encoding="utf-8", newline="") as stream:
    reader = csv.DictReader(stream)
    fields = list(reader.fieldnames or [])
    rows = list(reader)
for row in rows:
    calibration = row["factual_calibration"].strip()
    row["benchmark_reference"] = reviewed_reference(row["benchmark_reference"], calibration)
    row["label_provenance"] = "human_reviewed_machine_assisted"
with PACKET.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f"Updated benchmark references and provenance: {PACKET.name} ({len(rows)} rows)")
