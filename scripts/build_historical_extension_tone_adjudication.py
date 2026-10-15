"""Build a stable adjudication queue and final labels for the archive extension."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "data/corpus/historical/supplemental_validation"
KEY = ROOT / "data/corpus/historical/validation_internal/historical_extension_blind_key.csv"
OUT = PACKETS / "adjudication"; DECISIONS = OUT / "extension_tone_decisions.csv"
FIELDS = ["blind_id", "item_id", "text_representation", "text", "tone_a", "tone_b", "adjudicated_tone", "adjudication_status", "adjudicator", "adjudication_date", "adjudication_rationale"]

def read(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                return list(csv.DictReader(stream))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path}")
def clean(value: str | None) -> str: return (value or "").strip()

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); now = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
    a = {r["blind_id"]: r for r in read(PACKETS / "annotator_a.csv") if clean(r.get("label_provenance")) == "human_independent" and clean(r.get("tone"))}
    b = {r["blind_id"]: r for r in read(PACKETS / "annotator_b.csv") if clean(r.get("label_provenance")) == "human_independent" and clean(r.get("tone"))}
    key = {r["blind_id"]: r["item_id"] for r in read(KEY)}
    a = {blind_id: row for blind_id, row in a.items() if blind_id in key}
    b = {blind_id: row for blind_id, row in b.items() if blind_id in key}
    prior = {r["blind_id"]: r for r in read(DECISIONS)} if DECISIONS.exists() else {}
    final, queue, decisions = [], [], []
    for blind_id in sorted(set(a) & set(b)):
        left, right, old = a[blind_id], b[blind_id], prior.get(blind_id, {})
        differs = clean(left["tone"]) != clean(right["tone"]); resolved = not differs or bool(clean(old.get("adjudicated_tone")) and clean(old.get("adjudicator")))
        row = {"blind_id": blind_id, "item_id": key[blind_id], "text_representation": clean(left.get("text_representation")), "text": clean(left["text"]), "tone_a": clean(left["tone"]), "tone_b": clean(right["tone"]), "adjudicated_tone": clean(left["tone"]) if not differs else (clean(old.get("adjudicated_tone")) if resolved else ""), "adjudication_status": "extension_independent_consensus" if not differs else ("extension_manual_adjudication" if resolved else "needs_extension_tone_adjudication"), "adjudicator": "consensus_rule_v1" if not differs else clean(old.get("adjudicator")), "adjudication_date": now if not differs else clean(old.get("adjudication_date")), "adjudication_rationale": "independent annotators agreed" if not differs else clean(old.get("adjudication_rationale"))}
        final.append(row)
        if differs:
            decisions.append({field: row[field] for field in FIELDS if field != "item_id" and field != "adjudication_status"})
            if not resolved: queue.append(row)
    for path, rows, fields in ((DECISIONS, decisions, [field for field in FIELDS if field not in {"item_id", "adjudication_status"}]), (OUT / "extension_tone_adjudications.csv", final, FIELDS), (OUT / "extension_tone_adjudication_queue.csv", queue, FIELDS)):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    summary = {"paired": len(final), "consensus": sum(r["adjudication_status"] == "extension_independent_consensus" for r in final), "unresolved": len(queue), "ready": bool(final) and not queue}
    (OUT / "extension_tone_adjudication_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
