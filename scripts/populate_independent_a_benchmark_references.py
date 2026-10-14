"""Populate independent-packet references from matching item-level source context.

The factual label remains the independent packet's manually entered value. Only
the compact source/benchmark context is transferred from the prior packet.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "corpus" / "independent_validation" / "annotator_a.csv"
SOURCE = ROOT / "data" / "corpus" / "labeling" / "annotator_a.csv"
AUDIT = ROOT / "data" / "corpus" / "independent_validation" / "annotator_a_benchmark_reference_audit.json"


def main() -> None:
    with TARGET.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, target_rows = reader.fieldnames or [], list(reader)
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        source_rows = {row["item_id"]: row for row in csv.DictReader(stream)}
    required = {"item_id", "factual_calibration", "benchmark_reference"}
    if missing := required - set(fields):
        raise ValueError(f"Target is missing required fields: {sorted(missing)}")

    changes = []
    for row in target_rows:
        item_id = row["item_id"]
        source = source_rows.get(item_id)
        if source is None:
            raise ValueError(f"No matching source-context row for {item_id}")
        source_reference = source.get("benchmark_reference", "").strip()
        if not source_reference:
            raise ValueError(f"Source-context reference is blank for {item_id}")
        factual = row.get("factual_calibration", "").strip()
        if not factual:
            raise ValueError(f"Independent factual calibration is blank for {item_id}")
        tail = source_reference.split(";", 1)[1].strip() if ";" in source_reference else source_reference
        new_reference = f"Independent-packet review — {factual}; {tail}"
        changes.append({"item_id": item_id, "old_reference": row.get("benchmark_reference", ""), "new_reference": new_reference})
        row["benchmark_reference"] = new_reference

    temporary = TARGET.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(target_rows)
    temporary.replace(TARGET)
    audit = {
        "rows_updated": len(changes),
        "references_remaining_blank": sum(not row["benchmark_reference"].strip() for row in target_rows),
        "reference_context_source": str(SOURCE),
        "note": "Only benchmark_reference was modified. The status prefix was synchronized to the target packet's manually entered factual_calibration; source/benchmark context was transferred from the matching prior packet and is not an independent second-rater judgment.",
        "changes": changes,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
