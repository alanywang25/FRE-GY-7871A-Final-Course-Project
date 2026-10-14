"""Run source-name and political-name masking checks on the dictionary baseline."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from label_corpus_baseline_v3 import label

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "corpus" / "processed" / "balanced_analysis_sample.csv"
OUT = ROOT / "data" / "corpus" / "validation"
ACTORS = re.compile(r"\b(Trump|Biden|Republicans?|Democrats?|GOP|White House|Federal Reserve|Fed|Treasury|Congress)\b", re.I)
OUTLETS = re.compile(r"\b(CNN|Fox News|MSNBC|New York Times|Wall Street Journal|Reuters|Associated Press|AP|Bloomberg|CNBC|BBC)\b", re.I)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with INPUT.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    result = []
    for row in rows:
        original = label(row)["tone"]
        masked = row.copy()
        masked["text"] = ACTORS.sub("[ACTOR]", row["text"])
        actor_masked = label(masked)["tone"]
        source_masked = row.copy()
        source_text = OUTLETS.sub("[OUTLET]", row["text"])
        for source_key in ("source_name", "source_domain"):
            value = row.get(source_key, "").strip()
            if value:
                source_text = re.sub(re.escape(value), "[OUTLET]", source_text, flags=re.I)
        source_masked["text"] = source_text
        source_label = label(source_masked)["tone"]
        result.append({
            "item_id": row["item_id"], "original_tone": original,
            "actor_masked_tone": actor_masked, "source_masked_tone": source_label,
            "actor_changed": original != actor_masked, "source_changed": original != source_label,
        })
    with (OUT / "dictionary_actor_name_invariance.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    summary = {
        "records": len(result),
        "actor_changed_labels": sum(row["actor_changed"] for row in result),
        "actor_changed_label_rate": sum(row["actor_changed"] for row in result) / len(result),
        "source_changed_labels": sum(row["source_changed"] for row in result),
        "source_changed_label_rate": sum(row["source_changed"] for row in result) / len(result),
        "note": "Context-aware dictionary baseline v3. Actor and outlet masking are diagnostic checks, not a proof of fairness or invariance for a production model.",
    }
    (OUT / "dictionary_invariance_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
