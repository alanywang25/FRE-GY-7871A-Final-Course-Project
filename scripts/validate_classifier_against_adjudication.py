"""Evaluate the dictionary baseline against finalized independent tone adjudications."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ADJUDICATED = ROOT / "data" / "corpus" / "independent_validation" / "adjudication" / "independent_tone_adjudications.csv"
BASELINE = ROOT / "data" / "corpus" / "model_assisted" / "dictionary_baseline_v3.csv"
CORPUS = ROOT / "data" / "corpus" / "processed" / "balanced_analysis_sample.csv"
OUT = ROOT / "data" / "corpus" / "validation"


def score(frame: pd.DataFrame) -> dict:
    labels = sorted(set(frame["tone"]) | set(frame["predicted_tone"]))
    by_class = []
    for label in labels:
        tp = int(((frame.tone == label) & (frame.predicted_tone == label)).sum())
        fp = int(((frame.tone != label) & (frame.predicted_tone == label)).sum())
        fn = int(((frame.tone == label) & (frame.predicted_tone != label)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        by_class.append({"tone": label, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "support": int((frame.tone == label).sum())})
    return {"n": int(len(frame)), "accuracy": round(float((frame.tone == frame.predicted_tone).mean()), 3), "macro_f1": round(sum(x["f1"] for x in by_class) / len(by_class), 3) if by_class else None, "by_class": by_class}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    adjudicated = pd.read_csv(ADJUDICATED, dtype=str).fillna("").rename(columns={"adjudicated_tone": "tone"})
    baseline = pd.read_csv(BASELINE, dtype=str).fillna("")[["item_id", "tone"]].rename(columns={"tone": "predicted_tone"}).drop_duplicates("item_id")
    corpus = pd.read_csv(CORPUS, dtype=str).fillna("")[["item_id", "source_stratum"]].drop_duplicates("item_id")
    eligible = adjudicated.loc[adjudicated.adjudication_status.isin(["independent_consensus", "independent_manual_adjudication"]) & adjudicated.tone.ne("")].copy()
    merged = eligible.merge(baseline, on="item_id", how="inner").merge(corpus, on="item_id", how="left")
    summary = score(merged)
    summary["reference_status"] = "Finalized independently labeled and tone-adjudicated reference set. This validates tone only; other coding dimensions require their own adjudication."
    summary["evaluation_protocol"] = "Fixed, transparent context-aware dictionary rules. This is a development-set diagnostic; reserve a separate held-out labeled set for a final performance claim."
    pd.crosstab(merged.tone, merged.predicted_tone, dropna=False).to_csv(OUT / "dictionary_tone_confusion_matrix.csv")
    source_rows = []
    for source_stratum, group in merged.groupby("source_stratum", dropna=False):
        metrics = score(group)
        source_rows.append({"source_stratum": source_stratum or "missing", "n": metrics["n"], "accuracy": metrics["accuracy"], "macro_f1": metrics["macro_f1"]})
    pd.DataFrame(source_rows).to_csv(OUT / "dictionary_performance_by_source.csv", index=False)
    (OUT / "dictionary_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
