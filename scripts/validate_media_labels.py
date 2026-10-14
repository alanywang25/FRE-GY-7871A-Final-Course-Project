"""Validate independent human annotations without counting machine drafts as raters."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "corpus" / "independent_validation"
OUT = ROOT / "data" / "corpus" / "validation"


def eligible(path: Path, suffix: str) -> pd.DataFrame:
    # Spreadsheet exports may use Windows-1252 for punctuation/diacritics.
    # Preserve the original file and fall back only when UTF-8 decoding fails.
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            frame = pd.read_csv(path, dtype=str, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("unknown", b"", 0, 0, f"Cannot decode {path}")
    frame = frame.fillna("")
    independent = frame.get("label_provenance", pd.Series("", index=frame.index)).eq("human_independent")
    frame = frame.loc[independent & frame["tone"].str.strip().ne("")].copy()
    item_key = "corpus_id" if "corpus_id" in frame else "item_id"
    return frame[[item_key, "tone"]].rename(columns={item_key: "corpus_id", "tone": f"tone_{suffix}"})


def class_metrics(paired: pd.DataFrame) -> pd.DataFrame:
    labels = sorted(set(paired.get("tone_a", [])) | set(paired.get("tone_b", [])))
    rows = []
    for label in labels:
        tp = int(((paired.tone_a == label) & (paired.tone_b == label)).sum())
        fp = int(((paired.tone_a != label) & (paired.tone_b == label)).sum())
        fn = int(((paired.tone_a == label) & (paired.tone_b != label)).sum())
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
        rows.append({"tone": label, "support_a": int((paired.tone_a == label).sum()), "support_b": int((paired.tone_b == label).sum()), "agreement": tp, "precision_b_vs_a": precision, "recall_b_vs_a": recall, "f1_b_vs_a": f1})
    return pd.DataFrame(rows)


def cohen_kappa(a: pd.Series, b: pd.Series) -> float | None:
    if not len(a):
        return None
    labels = sorted(set(a) | set(b))
    observed = float((a == b).mean())
    expected = sum(float((a == label).mean() * (b == label).mean()) for label in labels)
    return None if np.isclose(1 - expected, 0) else round((observed - expected) / (1 - expected), 3)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    a, b = eligible(LABELS / "annotator_a.csv", "a"), eligible(LABELS / "annotator_b.csv", "b")
    paired = a.merge(b, on="corpus_id", how="inner")
    agreement = float((paired.tone_a == paired.tone_b).mean()) if len(paired) else None
    summary = {
        "eligible_human_a": int(len(a)), "eligible_human_b": int(len(b)),
        "paired_human_labels": int(len(paired)),
        "raw_tone_agreement": None if agreement is None else round(agreement, 3),
        "cohen_kappa": cohen_kappa(paired.tone_a, paired.tone_b),
        "gate_passed": bool(len(paired) >= 300),
        "message": "Validation gate passed; adjudicate disagreements before constructing media measures." if len(paired) >= 300 else "Blocked: fewer than 300 paired independent human labels. Machine-assisted and human-reviewed rows are intentionally excluded.",
    }
    paired.assign(agree=paired.tone_a == paired.tone_b).to_csv(OUT / "paired_human_tone_labels.csv", index=False)
    class_metrics(paired).to_csv(OUT / "human_tone_agreement_by_class.csv", index=False)
    (OUT / "label_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
