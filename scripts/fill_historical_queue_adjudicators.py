"""Set historical tone-queue adjudicators from entered tone selections."""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data/corpus/historical/independent_validation/adjudication/historical_tone_adjudication_queue.csv"
AUDIT = QUEUE.with_name("historical_tone_queue_adjudicator_audit.json")

def main() -> None:
    with QUEUE.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream); fields, rows = reader.fieldnames or [], list(reader)
    updates, unresolved = [], []
    for row in rows:
        selected_tone = row["adjudicated_tone"].strip()
        if selected_tone == row["tone_a"].strip(): selected = "a"
        elif selected_tone == row["tone_b"].strip(): selected = "b"
        else:
            unresolved.append({"blind_id": row["blind_id"], "reason": "blank or no match for adjudicated_tone"}); continue
        updates.append({"blind_id": row["blind_id"], "old_adjudicator": row.get("adjudicator", ""), "new_adjudicator": selected})
        row["adjudicator"] = selected
    if unresolved: raise ValueError(f"No file written; unresolved rows: {unresolved}")
    with QUEUE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    audit = {"rows_updated":len(updates), "selected_a":sum(x["new_adjudicator"]=="a" for x in updates), "selected_b":sum(x["new_adjudicator"]=="b" for x in updates), "values_changed":sum(x["old_adjudicator"]!=x["new_adjudicator"] for x in updates), "changes":updates}
    AUDIT.write_text(json.dumps(audit, indent=2), encoding="utf-8"); print(json.dumps({k:v for k,v in audit.items() if k!="changes"}, indent=2))

if __name__ == "__main__": main()
