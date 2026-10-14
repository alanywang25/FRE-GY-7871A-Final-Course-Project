"""Populate the two annotation packets with the reviewed dictionary baseline.

The inserted labels are explicitly marked machine_assisted. This script does not
create independent human annotations and the pipeline excludes these entries
from human-label completion counts.
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "corpus" / "model_assisted" / "dictionary_baseline_v1.csv"
PACKETS = [ROOT / "data" / "corpus" / "labeling" / "annotator_a.csv", ROOT / "data" / "corpus" / "labeling" / "annotator_b.csv"]


def load_labels() -> dict[str, dict]:
    with LABELS.open(encoding="utf-8", newline="") as stream:
        return {row["item_id"]: row for row in csv.DictReader(stream)}


def populate(path: Path, labels: dict[str, dict]) -> int:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    for extra in ("label_provenance", "model_name"):
        if extra not in fields:
            fields.append(extra)
    for row in rows:
        model = labels.get(row["item_id"])
        if model is None:
            raise KeyError(f"No model label for {row['item_id']}")
        for field in fields:
            if field in model and field not in {"item_id", "text", "text_representation"}:
                row[field] = model[field]
        row["label_provenance"] = "machine_assisted"
        row["model_name"] = "dictionary_baseline_v1"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> None:
    labels = load_labels()
    for packet in PACKETS:
        count = populate(packet, labels)
        print(f"Populated {packet.name}: {count} machine-assisted labels")


if __name__ == "__main__":
    main()
