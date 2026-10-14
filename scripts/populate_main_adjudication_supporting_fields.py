"""Populate consensus/supporting fields in main non-blinded adjudication decisions."""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADJUDICATION = ROOT / "data" / "corpus" / "adjudication"
REPORT = ADJUDICATION / "adjudication_difference_report.csv"
DECISIONS = ADJUDICATION / "manual_adjudication_decisions.csv"
ANNOTATOR_A = ROOT / "data" / "corpus" / "labeling" / "annotator_a.csv"
ANNOTATOR_B = ROOT / "data" / "corpus" / "labeling" / "annotator_b.csv"
AUDIT = ADJUDICATION / "main_adjudication_supporting_fields_audit.json"

CONSENSUS_FIELDS = [
    "salience_layoffs", "salience_hiring", "salience_price_level",
    "salience_disinflation", "salience_growth", "salience_recession_risk",
    "frame_price_level", "frame_inflation_rate", "frame_household_experience",
    "frame_national_aggregate", "frame_current", "frame_forecast",
    "political_attribution_target", "political_valence",
]
POPULATED_FIELDS = [*CONSENSUS_FIELDS, "factual_calibration", "benchmark_reference", "evidence_excerpt", "adjudicator"]


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def by_item(path: Path) -> dict[str, dict[str, str]]:
    _, rows = read(path)
    return {row["item_id"]: row for row in rows}


def main() -> None:
    report_fields, report = read(REPORT)
    decision_fields, decisions = read(DECISIONS)
    if "select" not in report_fields:
        raise ValueError("The difference report must have a select column.")
    selections: dict[str, dict[str, str]] = {}
    for row in report:
        choice = row.get("select", "").strip().casefold()
        if choice not in {"a", "b"}:
            raise ValueError(f"Invalid or blank select for {row['item_id']} / {row['field']}: {choice!r}")
        selections.setdefault(row["item_id"], {})[row["field"]] = choice

    a, b = by_item(ANNOTATOR_A), by_item(ANNOTATOR_B)
    changes: list[dict[str, str]] = []
    for decision in decisions:
        item_id = decision["item_id"]
        item_selections = selections.get(item_id)
        if not item_selections or item_id not in a or item_id not in b:
            raise ValueError(f"Missing selection or annotation for {item_id}.")
        if any(a[item_id].get(field, "") != b[item_id].get(field, "") for field in CONSENSUS_FIELDS):
            raise ValueError(f"Unexpected disagreement outside the difference report for {item_id}.")

        reference_choice = item_selections.get("factual_calibration") or item_selections.get("tone")
        source_for_reference = a[item_id] if reference_choice == "a" else b[item_id]
        source_for_factual = a[item_id] if item_selections.get("factual_calibration", reference_choice) == "a" else b[item_id]
        updates = {field: a[item_id].get(field, "") for field in CONSENSUS_FIELDS}
        updates["factual_calibration"] = source_for_factual.get("factual_calibration", "")
        updates["benchmark_reference"] = source_for_reference.get("benchmark_reference", "")
        updates["evidence_excerpt"] = source_for_reference.get("evidence_excerpt", "")
        updates["adjudicator"] = "+".join(sorted(set(item_selections.values())))
        for field, value in updates.items():
            old = decision.get(field, "")
            decision[field] = value
            if old != value:
                changes.append({"item_id": item_id, "field": field, "old_value": old, "new_value": value})

    temporary = DECISIONS.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decisions)
    temporary.replace(DECISIONS)
    audit = {
        "items_populated": len(decisions),
        "field_values_changed": len(changes),
        "adjudicator_counts": {choice: sum(row["adjudicator"] == choice for row in decisions) for choice in ("a", "b", "a+b")},
        "reference_rule": "factual_calibration selection when present; otherwise tone selection",
        "changes": changes,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
