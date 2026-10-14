"""Fill all-field annotator-A references without changing manual coding values.

The blind packet is linked internally to the original item-level annotator-A
packet.  This script transfers only the compact source/benchmark context and
prefixes it with the all-field packet's already-entered factual-calibration
value.  It intentionally leaves every other packet column unchanged.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/corpus/full_field_validation/annotator_a.csv"
KEY = ROOT / "data/corpus/validation_internal/full_field_validation_blind_key.csv"
SOURCE = ROOT / "data/corpus/labeling/annotator_a.csv"
AUDIT = ROOT / "data/corpus/full_field_validation/annotator_a_benchmark_reference_audit.json"


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]], str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                reader = csv.DictReader(stream)
                return reader.fieldnames or [], list(reader), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path}")


def main() -> None:
    fields, rows, input_encoding = read_rows(TARGET)
    required = {"blind_id", "factual_calibration", "benchmark_reference", "label_provenance"}
    if missing := required - set(fields):
        raise ValueError(f"Target is missing required columns: {sorted(missing)}")
    _, key_rows, _ = read_rows(KEY)
    blind_to_item = {row["blind_id"]: row["item_id"] for row in key_rows}
    _, source_rows, _ = read_rows(SOURCE)
    source_by_item = {row["item_id"]: row for row in source_rows}

    changes = []
    for row in rows:
        blind_id = row["blind_id"].strip()
        if not row["label_provenance"].strip().startswith("human_"):
            continue
        item_id = blind_to_item.get(blind_id)
        if not item_id:
            raise ValueError(f"No private blind-key match for {blind_id}")
        source_reference = source_by_item.get(item_id, {}).get("benchmark_reference", "").strip()
        if not source_reference:
            raise ValueError(f"No source-context reference for {blind_id} / {item_id}")
        factual = row["factual_calibration"].strip()
        if not factual:
            raise ValueError(f"Manual factual_calibration is blank for {blind_id}")
        context = source_reference.split(";", 1)[1].strip() if ";" in source_reference else source_reference
        updated = f"Independent all-field review — {factual}; {context}"
        changes.append({"blind_id": blind_id, "old_reference": row["benchmark_reference"], "new_reference": updated})
        row["benchmark_reference"] = updated

    with TARGET.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    audit = {
        "input_encoding": input_encoding,
        "rows_updated": len(changes),
        "references_remaining_blank": sum(not row["benchmark_reference"].strip() for row in rows),
        "reference_context_source": str(SOURCE.relative_to(ROOT)),
        "note": "Only benchmark_reference was modified. The prefix uses the all-field packet's manually entered factual_calibration; transferred context is not an independent second-rater judgment.",
        "changes": changes,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
