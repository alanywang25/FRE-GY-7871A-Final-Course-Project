"""Synchronize completed independent-tone queue decisions into the merge input."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "corpus" / "independent_validation" / "adjudication"
QUEUE = OUT / "independent_tone_adjudication_queue.csv"
DECISIONS = OUT / "independent_tone_decisions.csv"
AUDIT = OUT / "independent_tone_queue_sync_audit.json"
FIELDS = ["adjudicated_tone", "adjudicator", "adjudication_date", "adjudication_rationale"]


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def main() -> None:
    queue_fields, queue = read(QUEUE)
    decision_fields, decisions = read(DECISIONS)
    if set(FIELDS) - set(queue_fields) or set(FIELDS) - set(decision_fields):
        raise ValueError("Queue and decision files must contain all adjudication fields.")
    source = {row["item_id"]: row for row in queue}
    target = {row["item_id"]: row for row in decisions}
    if set(source) != set(target):
        raise ValueError("Queue and decision item IDs do not match; no changes written.")
    blank = [item_id for item_id, row in source.items() if any(not row[field].strip() for field in FIELDS)]
    if blank:
        raise ValueError(f"Queue has incomplete decisions; no changes written: {blank}")
    changes = []
    for item_id, row in target.items():
        queue_row = source[item_id]
        for field in FIELDS:
            old, new = row.get(field, ""), queue_row[field]
            row[field] = new
            changes.append({"item_id": item_id, "field": field, "old_value": old, "new_value": new})
    temporary = DECISIONS.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decisions)
    temporary.replace(DECISIONS)
    audit = {"items_synchronized": len(target), "field_values_synchronized": len(changes), "changes": changes}
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
