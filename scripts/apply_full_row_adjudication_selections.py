"""Copy requested supporting fields from the selected annotator into each decision row."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADJUDICATION = ROOT / "data" / "corpus" / "adjudication"
REPORT = ADJUDICATION / "adjudication_difference_report.csv"
DECISIONS = ADJUDICATION / "manual_adjudication_decisions.csv"
LABELS = ROOT / "data" / "corpus" / "labeling"
AUDIT = ADJUDICATION / "adjudication_full_row_merge_audit.json"
COPY_FIELDS = [
    "salience_layoffs", "salience_hiring", "salience_price_level", "salience_disinflation",
    "salience_growth", "salience_recession_risk", "frame_price_level", "frame_inflation_rate",
    "frame_household_experience", "frame_national_aggregate", "frame_current", "frame_forecast",
    "factual_calibration", "political_attribution_target", "political_valence", "benchmark_reference",
    "evidence_excerpt",
]


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def rows_by_id(path: Path) -> dict[str, dict[str, str]]:
    _, rows = read_rows(path)
    return {row["item_id"]: row for row in rows}


def main() -> None:
    _, report = read_rows(REPORT)
    decision_fields, decisions = read_rows(DECISIONS)
    a = rows_by_id(LABELS / "annotator_a.csv")
    b = rows_by_id(LABELS / "annotator_b.csv")
    missing_fields = sorted(set(COPY_FIELDS) - set(decision_fields))
    if missing_fields:
        raise ValueError(f"Decision file is missing requested fields: {missing_fields}")

    choices: dict[str, set[str]] = defaultdict(set)
    for row in report:
        choice = row.get("select", "").strip().casefold()
        if choice:
            if choice not in {"a", "b"}:
                raise ValueError(f"Invalid select value for {row['item_id']}: {choice!r}")
            choices[row["item_id"]].add(choice)
    conflicts = {item_id: sorted(values) for item_id, values in choices.items() if len(values) != 1}
    if conflicts:
        raise ValueError(f"Each item needs one consistent selection: {conflicts}")

    decision_by_id = {row["item_id"]: row for row in decisions}
    changes = []
    for item_id, options in choices.items():
        if item_id not in decision_by_id or item_id not in a or item_id not in b:
            raise ValueError(f"Missing a matching row for {item_id}")
        choice = next(iter(options))
        source = a[item_id] if choice == "a" else b[item_id]
        target = decision_by_id[item_id]
        for field in COPY_FIELDS:
            old_value, new_value = target.get(field, ""), source.get(field, "")
            target[field] = new_value
            changes.append({"item_id": item_id, "select": choice, "field": field, "old_value": old_value, "new_value": new_value})

    temporary = DECISIONS.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decisions)
    temporary.replace(DECISIONS)
    audit = {
        "items_updated": len(choices), "fields_copied_per_item": COPY_FIELDS,
        "field_values_applied": len(changes), "selected_a_items": sum(next(iter(v)) == "a" for v in choices.values()),
        "selected_b_items": sum(next(iter(v)) == "b" for v in choices.values()),
        "values_changed": sum(row["old_value"] != row["new_value"] for row in changes),
        "preserved_fields": ["tone", "adjudicator", "adjudication_date", "adjudication_rationale"],
        "changes": changes,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
