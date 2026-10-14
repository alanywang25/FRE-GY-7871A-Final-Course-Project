"""Populate adjudicator and rationale from the reviewed A/B selections."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADJUDICATION = ROOT / "data" / "corpus" / "adjudication"
REPORT = ADJUDICATION / "adjudication_difference_report.csv"
DECISIONS = ADJUDICATION / "manual_adjudication_decisions.csv"
AUDIT = ADJUDICATION / "adjudicator_rationale_merge_audit.json"


def main() -> None:
    with REPORT.open(encoding="utf-8", newline="") as stream:
        report = list(csv.DictReader(stream))
    with DECISIONS.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, decisions = reader.fieldnames or [], list(reader)
    required = {"adjudicator", "adjudication_rationale"}
    if missing := required - set(fields):
        raise ValueError(f"Decision file is missing columns: {sorted(missing)}")

    choices: dict[str, set[str]] = defaultdict(set)
    differences: dict[str, set[str]] = defaultdict(set)
    for row in report:
        item_id = row["item_id"]
        choice = row.get("select", "").strip().casefold()
        if choice not in {"a", "b"}:
            raise ValueError(f"Each report row needs select a or b: {item_id}")
        choices[item_id].add(choice)
        differences[item_id].add(row["field"])
    conflicting = {item_id: sorted(value) for item_id, value in choices.items() if len(value) != 1}
    if conflicting:
        raise ValueError(f"Conflicting selections by item: {conflicting}")

    changes = []
    for decision in decisions:
        item_id = decision["item_id"]
        if item_id not in choices:
            continue
        diff = differences[item_id]
        if diff == {"tone"}:
            rationale = "mismatch in tone"
        elif diff == {"factual_calibration"}:
            rationale = "mismatch in factual_calibration"
        elif diff == {"tone", "factual_calibration"}:
            rationale = "mismatch in factual_calibration and tone"
        else:
            raise ValueError(f"Unexpected disagreement fields for {item_id}: {sorted(diff)}")
        choice = next(iter(choices[item_id]))
        changes.append({
            "item_id": item_id, "old_adjudicator": decision.get("adjudicator", ""),
            "new_adjudicator": choice, "old_rationale": decision.get("adjudication_rationale", ""),
            "new_rationale": rationale,
        })
        decision["adjudicator"] = choice
        decision["adjudication_rationale"] = rationale

    temporary = DECISIONS.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(decisions)
    temporary.replace(DECISIONS)
    audit = {
        "items_updated": len(changes), "adjudicator_a": sum(c["new_adjudicator"] == "a" for c in changes),
        "adjudicator_b": sum(c["new_adjudicator"] == "b" for c in changes),
        "rationale_counts": {r: sum(c["new_rationale"] == r for c in changes) for r in sorted({c["new_rationale"] for c in changes})},
        "changes": changes,
    }
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()
