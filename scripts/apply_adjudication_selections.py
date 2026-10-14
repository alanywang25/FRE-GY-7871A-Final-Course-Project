"""Apply reviewed A/B selections to the matching disputed decision fields only."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADJUDICATION = ROOT / "data" / "corpus" / "adjudication"
REPORT = ADJUDICATION / "adjudication_difference_report.csv"
DECISIONS = ADJUDICATION / "manual_adjudication_decisions.csv"
LABELS = ROOT / "data" / "corpus" / "labeling"
AUDIT = ADJUDICATION / "adjudication_selection_merge_audit.json"


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def by_id(path: Path) -> dict[str, dict[str, str]]:
    _, rows = read_rows(path)
    return {row["item_id"]: row for row in rows}


def main() -> None:
    report_fields, report = read_rows(REPORT)
    decision_fields, decisions = read_rows(DECISIONS)
    if "select" not in report_fields:
        raise ValueError("The difference report must include a select column containing a or b.")
    a = by_id(LABELS / "annotator_a.csv")
    b = by_id(LABELS / "annotator_b.csv")
    decision_by_id = {row["item_id"]: row for row in decisions}
    changes: list[dict[str, str]] = []
    invalid: list[dict[str, str]] = []

    for row in report:
        choice = row.get("select", "").strip().casefold()
        if not choice:
            continue
        if choice not in {"a", "b"}:
            invalid.append({"item_id": row.get("item_id", ""), "field": row.get("field", ""), "select": choice})
            continue
        item_id, field = row["item_id"], row["field"]
        if item_id not in decision_by_id or item_id not in a or item_id not in b:
            raise ValueError(f"Missing matching decision or annotation row for {item_id}.")
        if field not in decision_fields:
            raise ValueError(f"Decision template has no field named {field!r}.")
        source = a if choice == "a" else b
        new_value = source[item_id].get(field, "")
        old_value = decision_by_id[item_id].get(field, "")
        decision_by_id[item_id][field] = new_value
        changes.append({"item_id": item_id, "field": field, "select": choice, "old_value": old_value, "new_value": new_value})

    if invalid:
        raise ValueError(f"Invalid select values: {invalid}")
    if not changes:
        raise ValueError("No nonblank selections were found; the decision file was not changed.")

    temporary = DECISIONS.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decisions)
    temporary.replace(DECISIONS)
    audit = {
        "selected_fields_applied": len(changes),
        "items_touched": len({change["item_id"] for change in changes}),
        "selected_a": sum(change["select"] == "a" for change in changes),
        "selected_b": sum(change["select"] == "b" for change in changes),
        "fields": sorted({change["field"] for change in changes}),
        "changes": changes,
        "note": "Only the selected disputed field was replaced. Existing adjudicator, date, rationale, evidence, and non-disputed decision fields were preserved.",
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
