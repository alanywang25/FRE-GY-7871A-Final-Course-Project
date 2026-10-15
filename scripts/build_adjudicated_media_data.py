"""Build an auditable consensus dataset and availability-dated monthly media measures.

This program never invents an adjudicator decision. Rows with any disagreement
between the two reviewed packets are retained in a queue and excluded from the
monthly measures until a named human adjudicator resolves them.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus" / "processed" / "balanced_analysis_sample.csv"
LABEL_DIR = ROOT / "data" / "corpus" / "labeling"
OUT = ROOT / "data" / "corpus" / "adjudication"
MONTHLY = ROOT / "data" / "media_monthly.csv"
DECISIONS = OUT / "manual_adjudication_decisions.csv"

CODING_FIELDS = [
    "tone", "salience_layoffs", "salience_hiring", "salience_price_level",
    "salience_disinflation", "salience_growth", "salience_recession_risk",
    "frame_price_level", "frame_inflation_rate", "frame_household_experience",
    "frame_national_aggregate", "frame_current", "frame_forecast",
    "factual_calibration", "political_attribution_target", "political_valence",
]
EVIDENCE_FIELDS = ["benchmark_reference", "evidence_excerpt"]


def rows_by_id(path: Path) -> dict[str, dict[str, str]]:
    """Keep the first packet record for an item; repeated IDs are collection duplicates."""
    records: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            records.setdefault(row["item_id"], row)
    return records


def normalized(value: str | None) -> str:
    return (value or "").strip()


def mean(rows: list[dict[str, str]], predicate) -> str:
    if not rows:
        return ""
    return f"{sum(bool(predicate(row)) for row in rows) / len(rows):.6f}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
    with CORPUS.open(encoding="utf-8", newline="") as stream:
        corpus_rows = list(csv.DictReader(stream))
    corpus = {row["item_id"]: row for row in corpus_rows}
    a = rows_by_id(LABEL_DIR / "annotator_a.csv")
    b = rows_by_id(LABEL_DIR / "annotator_b.csv")
    all_ids = sorted(set(corpus) & set(a) & set(b))
    existing_decisions: dict[str, dict[str, str]] = {}
    if DECISIONS.exists():
        with DECISIONS.open(encoding="utf-8", newline="") as stream:
            existing_decisions = {row["item_id"]: row for row in csv.DictReader(stream) if row.get("item_id")}
    adjudicated, queue = [], []
    for item_id in all_ids:
        source, left, right = corpus[item_id], a[item_id], b[item_id]
        disagreements = [field for field in CODING_FIELDS if normalized(left.get(field)) != normalized(right.get(field))]
        decision = existing_decisions.get(item_id, {})
        decision_complete = bool(decision.get("adjudicator", "").strip()) and all(
            decision.get(field, "").strip() for field in disagreements
        )
        consensus = not disagreements
        resolved = consensus or decision_complete
        publication = normalized(source.get("published_at"))
        resolved_at = normalized(decision.get("adjudication_date")) if decision_complete else built_at
        output = {
            "item_id": item_id,
            "month": publication[:7] + "-01" if len(publication) >= 7 else "",
            "published_at": publication,
            "publisher_url": normalized(source.get("publisher_url")),
            "source_name": normalized(source.get("source_name")),
            "source_domain": normalized(source.get("source_domain")),
            "source_stratum": normalized(source.get("source_stratum")),
            "platform": normalized(source.get("platform")),
            "text_representation": normalized(source.get("text_representation")),
            "include_default": normalized(source.get("include_default")),
            "is_duplicate": normalized(source.get("is_duplicate")),
            "suspected_automated": normalized(source.get("suspected_automated")),
            "text": normalized(source.get("text")),
            "adjudication_status": "consensus_human_reviewed" if consensus else ("adjudicated_manual" if decision_complete else "needs_human_adjudication"),
            "adjudicated_by": "consensus_rule_v1" if consensus else decision.get("adjudicator", ""),
            "adjudicated_at": resolved_at if resolved else "",
            "availability_timestamp": resolved_at if resolved else "",
            "disagreement_fields": ";".join(disagreements),
            "annotator_a_provenance": normalized(left.get("label_provenance")),
            "annotator_b_provenance": normalized(right.get("label_provenance")),
        }
        for field in CODING_FIELDS + EVIDENCE_FIELDS:
            output[f"annotator_a_{field}"] = normalized(left.get(field))
            output[f"annotator_b_{field}"] = normalized(right.get(field))
            output[field] = normalized(left.get(field)) if consensus else (normalized(decision.get(field)) if decision_complete and field in disagreements else (normalized(left.get(field)) if decision_complete else ""))
        if decision_complete:
            output["benchmark_reference"] = normalized(decision.get("benchmark_reference")) or output["benchmark_reference"]
            output["evidence_excerpt"] = normalized(decision.get("evidence_excerpt")) or output["evidence_excerpt"]
        output["analysis_include"] = str(
            resolved and normalized(source.get("include_default")).casefold() == "true"
            and normalized(source.get("is_duplicate")).casefold() != "true"
            and normalized(source.get("suspected_automated")).casefold() != "true"
        ).lower()
        adjudicated.append(output)
        if not resolved:
            queue.append(output)

    fields = list(adjudicated[0])
    for name, rows in [("adjudicated_item_labels.csv", adjudicated), ("adjudication_queue.csv", queue)]:
        with (OUT / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    decision_fields = ["item_id", *CODING_FIELDS, "benchmark_reference", "evidence_excerpt", "adjudicator", "adjudication_date", "adjudication_rationale"]
    template_rows = []
    for row in queue:
        existing = existing_decisions.get(row["item_id"], {})
        template_rows.append({field: existing.get(field, "") for field in decision_fields} | {"item_id": row["item_id"]})
    with DECISIONS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(template_rows)

    by_month: dict[str, list[dict[str, str]]] = defaultdict(list)
    candidate_by_month: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in adjudicated:
        candidate = (row["include_default"].casefold() == "true" and row["is_duplicate"].casefold() != "true" and row["suspected_automated"].casefold() != "true")
        if candidate:
            candidate_by_month[row["month"]].append(row)
        if row["analysis_include"] == "true":
            by_month[row["month"]].append(row)

    monthly_rows = []
    for month in sorted(candidate_by_month):
        valid, candidates = by_month[month], candidate_by_month[month]
        monthly_rows.append({
            "month": month,
            "available_on": built_at,
            "aggregate_status": "provisional_consensus_human_reviewed",
            "tone_negative_share": mean(valid, lambda r: r["tone"] == "negative"),
            "tone_positive_share": mean(valid, lambda r: r["tone"] == "positive"),
            "tone_mixed_share": mean(valid, lambda r: r["tone"] == "mixed"),
            "price_level_frame_share": mean(valid, lambda r: r["frame_price_level"] == "1"),
            "recession_salience_share": mean(valid, lambda r: r["salience_recession_risk"] == "1"),
            "factual_calibrated_share": mean(valid, lambda r: r["factual_calibration"] == "calibrated"),
            "factual_materially_incomplete_share": mean(valid, lambda r: r["factual_calibration"] == "materially incomplete-or-misleading"),
            "corpus_items": len(valid),
            "eligible_items": len(candidates),
            "unresolved_items": len(candidates) - len(valid),
            "source_count": len({r["source_domain"] for r in valid if r["source_domain"]}),
            "missingness_rate": f"{1 - (len(valid) / len(candidates) if candidates else 0):.6f}",
            "notes": "Consensus-only aggregation. Disagreements and excluded duplicates/automated posts are not treated as zero; availability is adjudication-build time, not publication time.",
        })
    monthly_fields = list(monthly_rows[0]) if monthly_rows else []
    with MONTHLY.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=monthly_fields)
        writer.writeheader()
        writer.writerows(monthly_rows)
    summary = {
        "built_at": built_at,
        "unique_items": len(adjudicated),
        "consensus_items": sum(row["adjudication_status"] == "consensus_human_reviewed" for row in adjudicated),
        "manual_adjudications": sum(row["adjudication_status"] == "adjudicated_manual" for row in adjudicated),
        "needs_human_adjudication": len(queue),
        "monthly_rows": len(monthly_rows),
        "provenance": "Consensus between two human-reviewed, non-blinded packets. This is not an independent-annotator reliability result.",
    }
    (OUT / "adjudication_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
