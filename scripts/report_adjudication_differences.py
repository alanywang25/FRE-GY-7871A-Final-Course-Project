"""Create a human-readable, field-level audit of every queued disagreement."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "corpus" / "labeling"
ADJUDICATION = ROOT / "data" / "corpus" / "adjudication"
QUEUE = ADJUDICATION / "adjudication_queue.csv"
CSV_OUTPUT = ADJUDICATION / "adjudication_difference_report.csv"
MD_OUTPUT = ADJUDICATION / "adjudication_difference_outline.md"


def read_by_id(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return {row["item_id"]: row for row in csv.DictReader(stream)}


def clean(value: str | None) -> str:
    return (value or "").strip()


def main() -> None:
    a = read_by_id(LABELS / "annotator_a.csv")
    b = read_by_id(LABELS / "annotator_b.csv")
    with QUEUE.open(encoding="utf-8", newline="") as stream:
        queued = list(csv.DictReader(stream))

    rows: list[dict[str, str]] = []
    by_item: dict[str, list[dict[str, str]]] = {}
    counts: Counter[str] = Counter()
    for item in queued:
        item_id = item["item_id"]
        fields = [field for field in clean(item.get("disagreement_fields")).split(";") if field]
        item_rows = []
        for field in fields:
            result = {
                "item_id": item_id,
                "field": field,
                "annotator_a_value": clean(a[item_id].get(field)),
                "annotator_b_value": clean(b[item_id].get(field)),
                "text_representation": clean(item.get("text_representation")),
                "text": clean(item.get("text")),
            }
            rows.append(result)
            item_rows.append(result)
            counts[field] += 1
        by_item[item_id] = item_rows

    with CSV_OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["item_id", "field", "annotator_a_value", "annotator_b_value", "text_representation", "text"])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Adjudication difference outline",
        "",
        f"Queued items: {len(queued)}  ",
        f"Field-level disagreements: {len(rows)}",
        "",
        "## Disagreement counts by field",
        "",
    ]
    lines.extend(f"- `{field}`: {count}" for field, count in sorted(counts.items()))
    for item in queued:
        item_id = item["item_id"]
        lines.extend(["", f"## {item_id}", "", f"**Text ({clean(item.get('text_representation'))}):** {clean(item.get('text'))}", ""])
        for difference in by_item[item_id]:
            lines.append(f"- `{difference['field']}` — A: `{difference['annotator_a_value']}`; B: `{difference['annotator_b_value']}`")
    MD_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} field-level differences for {len(queued)} queued items.")


if __name__ == "__main__":
    main()
