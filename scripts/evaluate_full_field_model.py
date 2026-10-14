"""Score the dictionary baseline against finalized all-field human labels."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from build_full_field_validation_packets import CODE_FIELDS


ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data/corpus/full_field_validation/adjudication/full_field_adjudicated_labels.csv"
# v1 is the transparent multi-field dictionary. v3 predicts tone only and is
# retained for the separate tone-model workflow.
BASELINE = ROOT / "data/corpus/model_assisted/dictionary_baseline_v1.csv"
OUT = ROOT / "data/corpus/validation"
DETAIL = OUT / "full_field_model_performance_by_field_class_source.csv"
SUMMARY = OUT / "full_field_model_evaluation_summary.json"


def read(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding).fillna("")
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {path}")


def metrics(gold: pd.Series, predicted: pd.Series, label: str) -> tuple[int, float | None, float | None, float | None, float | None]:
    support = int(gold.eq(label).sum())
    predicted_count = int(predicted.eq(label).sum())
    true_positive = int((gold.eq(label) & predicted.eq(label)).sum())
    total = len(gold)
    accuracy = None if not total else round(float(gold.eq(predicted).mean()), 3)
    precision = None if not predicted_count else round(true_positive / predicted_count, 3)
    recall = None if not support else round(true_positive / support, 3)
    f1 = None if precision is None or recall is None or precision + recall == 0 else round(2 * precision * recall / (precision + recall), 3)
    return support, accuracy, precision, recall, f1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-held-out", action="store_true", help="Score the 60 held-out items after the model is locked.")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    empty_columns = ["evaluation_split", "source_stratum", "field", "class", "n", "support", "accuracy", "precision", "recall", "f1"]
    if not GOLD.exists() or not BASELINE.exists():
        pd.DataFrame(columns=empty_columns).to_csv(DETAIL, index=False)
        SUMMARY.write_text(json.dumps({"ready": False, "message": "Missing finalized human labels or dictionary baseline."}, indent=2), encoding="utf-8")
        return
    gold, baseline = read(GOLD), read(BASELINE)
    required = set(CODE_FIELDS + ["item_id", "source_stratum", "evaluation_split"])
    ready = len(gold) >= 300 and required.issubset(gold.columns) and set(CODE_FIELDS + ["item_id"]).issubset(baseline.columns)
    if not ready:
        pd.DataFrame(columns=empty_columns).to_csv(DETAIL, index=False)
        SUMMARY.write_text(json.dumps({"ready": False, "adjudicated_rows": len(gold), "message": "Await at least 300 finalized all-field human labels."}, indent=2), encoding="utf-8")
        return
    # The source corpus retains three duplicate observations; score one fixed
    # dictionary output per adjudicated item rather than multiplying a gold row.
    baseline = baseline.drop_duplicates("item_id", keep="first")
    paired = gold.merge(baseline[["item_id", *CODE_FIELDS]], on="item_id", how="inner", suffixes=("_gold", "_model"), validate="one_to_one")
    for field in ("political_attribution_target", "political_valence"):
        paired[f"{field}_model"] = paired[f"{field}_model"].replace("", "none")
    scored = paired if args.release_held_out else paired.loc[paired.evaluation_split.eq("development")].copy()
    rows = []
    for field in CODE_FIELDS:
        for (split, stratum), group in scored.groupby(["evaluation_split", "source_stratum"], dropna=False):
            truth, predicted = group[f"{field}_gold"], group[f"{field}_model"]
            for label in sorted(set(truth) | set(predicted)):
                support, accuracy, precision, recall, f1 = metrics(truth, predicted, label)
                rows.append({"evaluation_split": split, "source_stratum": stratum, "field": field, "class": label, "n": len(group), "support": support, "accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1})
    pd.DataFrame(rows, columns=empty_columns).to_csv(DETAIL, index=False)
    file_hash = hashlib.sha256(BASELINE.read_bytes()).hexdigest()
    held_out = paired.loc[paired.evaluation_split.eq("held_out")]
    summary = {
        "ready": True,
        "gold_rows": len(gold),
        "paired_rows": len(paired),
        "scored_rows": len(scored),
        "held_out_rows": len(held_out),
        "development_rows": int(paired.evaluation_split.eq("development").sum()),
        "baseline_file": str(BASELINE.relative_to(ROOT)),
        "baseline_sha256": file_hash,
        "held_out_released": args.release_held_out,
        "final_performance_claim": "not authorized" if not args.release_held_out else "held-out diagnostic only; retain this run's baseline SHA-256 and do not tune further.",
        "next_step": "Revise only with development IDs, lock the model, then rerun with --release-held-out exactly once for the final held-out claim." if not args.release_held_out else "Do not tune the model after releasing held-out results.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
