"""Create and maintain an auditable adjudication workflow for independent tone labels."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "data" / "corpus" / "independent_validation"
OUT = PACKETS / "adjudication"
DECISIONS = OUT / "independent_tone_decisions.csv"
FINAL = OUT / "independent_tone_adjudications.csv"
QUEUE = OUT / "independent_tone_adjudication_queue.csv"
SUMMARY = OUT / "independent_tone_adjudication_summary.json"


def read_rows(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                return list(csv.DictReader(stream))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 0, f"Cannot decode {path}")


def clean(value: str | None) -> str:
    return (value or "").strip()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
    a = {row["item_id"]: row for row in read_rows(PACKETS / "annotator_a.csv") if clean(row.get("label_provenance")) == "human_independent" and clean(row.get("tone"))}
    b = {row["item_id"]: row for row in read_rows(PACKETS / "annotator_b.csv") if clean(row.get("label_provenance")) == "human_independent" and clean(row.get("tone"))}
    if not a or not b:
        raise ValueError("Independent packets need completed tone labels with human_independent provenance.")
    existing = {row["item_id"]: row for row in read_rows(DECISIONS)} if DECISIONS.exists() else {}

    final_rows, queue_rows, decisions = [], [], []
    for item_id in sorted(set(a) & set(b)):
        left, right = a[item_id], b[item_id]
        different = clean(left["tone"]) != clean(right["tone"])
        decision = existing.get(item_id, {})
        manual_tone = clean(decision.get("adjudicated_tone"))
        adjudicator = clean(decision.get("adjudicator"))
        resolved = not different or bool(manual_tone and adjudicator)
        status = "independent_consensus" if not different else ("independent_manual_adjudication" if resolved else "needs_independent_tone_adjudication")
        final = {
            "item_id": item_id, "text_representation": clean(left.get("text_representation")), "text": clean(left.get("text")),
            "tone_a": clean(left["tone"]), "tone_b": clean(right["tone"]),
            "adjudicated_tone": clean(left["tone"]) if not different else (manual_tone if resolved else ""),
            "adjudication_status": status, "adjudicator": "consensus_rule_v1" if not different else adjudicator,
            "adjudication_date": built_at if not different else clean(decision.get("adjudication_date")),
            "adjudication_rationale": "independent annotators agreed" if not different else clean(decision.get("adjudication_rationale")),
        }
        final_rows.append(final)
        if different:
            template = {
                "item_id": item_id, "text_representation": final["text_representation"], "text": final["text"],
                "tone_a": final["tone_a"], "tone_b": final["tone_b"],
                "adjudicated_tone": manual_tone, "adjudicator": adjudicator,
                "adjudication_date": clean(decision.get("adjudication_date")),
                "adjudication_rationale": clean(decision.get("adjudication_rationale")),
            }
            decisions.append(template)
            if not resolved:
                queue_rows.append(final)

    decision_fields = ["item_id", "text_representation", "text", "tone_a", "tone_b", "adjudicated_tone", "adjudicator", "adjudication_date", "adjudication_rationale"]
    final_fields = list(final_rows[0])
    for path, fields, rows in ((DECISIONS, decision_fields, decisions), (FINAL, final_fields, final_rows), (QUEUE, final_fields, queue_rows)):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "built_at": built_at, "paired_independent_labels": len(final_rows),
        "independent_consensus": sum(row["adjudication_status"] == "independent_consensus" for row in final_rows),
        "manual_adjudications": sum(row["adjudication_status"] == "independent_manual_adjudication" for row in final_rows),
        "unresolved": len(queue_rows), "ready": len(queue_rows) == 0,
        "message": "Independent tone adjudication is complete." if not queue_rows else "Independent tone decisions are required before media measures can be finalized.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Independent tone adjudication\n\nResolve each row in `independent_tone_decisions.csv` by supplying `adjudicated_tone`, a named `adjudicator`, date, and rationale. Re-run `scripts/build_independent_tone_adjudication.py`; the queue and final tone dataset update while the original packets remain unchanged.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
