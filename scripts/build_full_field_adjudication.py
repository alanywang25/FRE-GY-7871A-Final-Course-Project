"""Create and validate adjudication materials for blinded all-field validation."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from build_full_field_validation_packets import CODE_FIELDS, INTERNAL, KEY, OUT


ADJUDICATION = OUT / "adjudication"
DECISIONS = ADJUDICATION / "full_field_decisions.csv"
FINAL = ADJUDICATION / "full_field_adjudicated_labels.csv"
QUEUE = ADJUDICATION / "full_field_adjudication_queue.csv"
SUMMARY = ADJUDICATION / "full_field_adjudication_summary.json"
REQUIRED_DECISION_METADATA = [
    "adjudicator", "adjudication_date", "adjudication_rationale",
    "evidence_excerpt", "benchmark_reference",
]


def read(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding).fillna("")
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {path}")


def decision_columns() -> list[str]:
    columns = ["blind_id", "disagreement_fields"]
    for field in CODE_FIELDS:
        columns.extend([f"{field}_a", f"{field}_b", f"adjudicated_{field}"])
    return columns + REQUIRED_DECISION_METADATA


def complete_rows(packet: pd.DataFrame, expected: set[str]) -> pd.DataFrame:
    packet = packet.loc[
        packet.blind_id.isin(expected) & packet.label_provenance.eq("human_independent")
    ].copy()
    complete = packet[CODE_FIELDS].ne("").all(axis=1)
    factual_evidence = packet.factual_calibration.eq("unverifiable") | (
        packet.benchmark_reference.ne("") & packet.evidence_excerpt.ne("")
    )
    return packet.loc[complete & factual_evidence].drop_duplicates("blind_id", keep="first")


def main() -> None:
    key = read(KEY)
    expected = set(key.blind_id)
    a = complete_rows(read(OUT / "annotator_a.csv"), expected)
    b = complete_rows(read(OUT / "annotator_b.csv"), expected)
    paired = a.merge(b, on="blind_id", suffixes=("_a", "_b"))
    paired = paired.merge(key, on="blind_id", how="left")

    ADJUDICATION.mkdir(parents=True, exist_ok=True)
    previous = read(DECISIONS) if DECISIONS.exists() else pd.DataFrame(columns=decision_columns())
    if "blind_id" not in previous:
        previous = pd.DataFrame(columns=decision_columns())
    previous = previous.drop_duplicates("blind_id", keep="last").set_index("blind_id", drop=False)
    decisions, final_rows, unresolved = [], [], []
    today = date.today().isoformat()
    for _, row in paired.iterrows():
        differences = [field for field in CODE_FIELDS if row[f"{field}_a"] != row[f"{field}_b"]]
        prior = previous.loc[row.blind_id].to_dict() if row.blind_id in previous.index else {}
        decision = {column: "" for column in decision_columns()}
        decision["blind_id"] = row.blind_id
        decision["disagreement_fields"] = "; ".join(differences)
        final = {
            "blind_id": row.blind_id,
            "item_id": row.item_id,
            "source_stratum": row.source_stratum,
            "evaluation_split": row.evaluation_split,
            "publication_date": row.published_at[:10],
            "text": row.text_a,
            "text_representation": row.text_representation_a,
            "disagreement_fields": "; ".join(differences),
        }
        for field in CODE_FIELDS:
            decision[f"{field}_a"] = row[f"{field}_a"]
            decision[f"{field}_b"] = row[f"{field}_b"]
            decision[f"adjudicated_{field}"] = prior.get(f"adjudicated_{field}", "")
            final[field] = row[f"{field}_a"] if field not in differences else decision[f"adjudicated_{field}"]
        if differences:
            for field in REQUIRED_DECISION_METADATA:
                decision[field] = prior.get(field, "")
            complete_decision = all(decision[field] for field in REQUIRED_DECISION_METADATA) and all(
                decision[f"adjudicated_{field}"] for field in differences
            )
            if not complete_decision:
                unresolved.append(decision)
                decisions.append(decision)
                continue
            final.update({field: decision[field] for field in REQUIRED_DECISION_METADATA})
            final["label_provenance"] = "human_independent_adjudicated"
        else:
            final.update({
                "adjudicator": "independent-consensus",
                "adjudication_date": today,
                "adjudication_rationale": "independent consensus across all required fields",
                "evidence_excerpt": row.evidence_excerpt_a,
                "benchmark_reference": row.benchmark_reference_a,
                "label_provenance": "human_independent_consensus",
            })
        if differences:
            decisions.append(decision)
        final_rows.append(final)

    pd.DataFrame(decisions, columns=decision_columns()).to_csv(DECISIONS, index=False)
    pd.DataFrame(unresolved, columns=decision_columns()).to_csv(QUEUE, index=False)
    final_columns = [
        "blind_id", "item_id", "source_stratum", "evaluation_split", "publication_date", "text",
        "text_representation", "disagreement_fields", *CODE_FIELDS, *REQUIRED_DECISION_METADATA,
        "label_provenance",
    ]
    pd.DataFrame(final_rows, columns=final_columns).to_csv(FINAL, index=False)
    summary = {
        "expected_blinded_items": len(expected),
        "paired_complete_all_fields": len(paired),
        "items_with_any_disagreement": len(decisions),
        "unresolved_items": len(unresolved),
        "adjudicated_or_consensus_items": len(final_rows),
        "gate_passed": len(final_rows) == len(expected) >= 300 and not unresolved,
        "message": "All-field adjudication gate passed." if len(final_rows) == len(expected) >= 300 and not unresolved else "Blocked: complete both packets and resolve every disagreement with all required metadata.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (ADJUDICATION / "README.md").write_text(
        "# All-field adjudication\n\nOnly rows that differ between independent reviewers appear in the decision queue. For each one, record all differing `adjudicated_*` values plus a named adjudicator, ISO date, rationale, evidence excerpt, and compact official benchmark reference. Rerun this script after saving decisions; the adjudicated export contains only consensus or fully resolved items.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
