"""Set independent-tone queue adjudicators from an entered adjudicated tone."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "corpus" / "independent_validation" / "adjudication" / "independent_tone_adjudication_queue.csv"
AUDIT = QUEUE.with_name("independent_tone_queue_adjudicator_audit.json")


def main() -> None:
    with QUEUE.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames or [], list(reader)
    required = {"tone_a", "tone_b", "adjudicated_tone", "adjudicator"}
    if missing := required - set(fields):
        raise ValueError(f"Queue is missing columns: {sorted(missing)}")
    changes, unresolved = [], []
    for row in rows:
        tone = row["adjudicated_tone"].strip()
        if not tone:
            unresolved.append({"item_id": row["item_id"], "reason": "blank adjudicated_tone"})
            continue
        if tone == row["tone_a"].strip():
            selected = "a"
        elif tone == row["tone_b"].strip():
            selected = "b"
        else:
            unresolved.append({"item_id": row["item_id"], "reason": "adjudicated_tone matches neither tone_a nor tone_b"})
            continue
        changes.append({"item_id": row["item_id"], "old_adjudicator": row.get("adjudicator", ""), "new_adjudicator": selected})
        row["adjudicator"] = selected
    if unresolved:
        raise ValueError(f"Queue contains non-resolvable rows; no file was written: {unresolved}")
    temporary = QUEUE.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(QUEUE)
    audit = {
        "rows_updated": len(changes), "selected_a": sum(c["new_adjudicator"] == "a" for c in changes),
        "selected_b": sum(c["new_adjudicator"] == "b" for c in changes),
        "values_changed": sum(c["old_adjudicator"] != c["new_adjudicator"] for c in changes),
        "changes": changes,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
