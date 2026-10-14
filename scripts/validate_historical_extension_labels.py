"""Validate paired independent labels for the historical-extension packet."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "data/corpus/historical/supplemental_validation"
OUT = ROOT / "data/corpus/historical/validation"
KEY = ROOT / "data/corpus/historical/validation_internal/historical_extension_blind_key.csv"
VALID_TONES = {"negative", "mixed", "neutral", "positive"}


def kappa(left: pd.Series, right: pd.Series) -> float | None:
    if not len(left): return None
    observed = (left == right).mean(); expected = sum((left == value).mean() * (right == value).mean() for value in sorted(set(left) | set(right)))
    return None if expected == 1 else round(float((observed - expected) / (1 - expected)), 3)


def main() -> None:
    def read_packet(path: Path) -> pd.DataFrame:
        for encoding in ("utf-8-sig", "cp1252"):
            try:
                return pd.read_csv(path, dtype=str, encoding=encoding).fillna("")
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode {path}")

    a_all = read_packet(PACKETS / "annotator_a.csv")
    b_all = read_packet(PACKETS / "annotator_b.csv")
    expected_ids = set(pd.read_csv(KEY, dtype=str).fillna("")["blind_id"])
    extra_rows = {
        "annotator_a": int((~a_all.blind_id.isin(expected_ids)).sum()),
        "annotator_b": int((~b_all.blind_id.isin(expected_ids)).sum()),
    }
    a = a_all.loc[a_all.blind_id.isin(expected_ids) & (a_all.label_provenance == "human_independent") & a_all.tone.isin(VALID_TONES)]
    b = b_all.loc[b_all.blind_id.isin(expected_ids) & (b_all.label_provenance == "human_independent") & b_all.tone.isin(VALID_TONES)]
    invalid_tones = int(
        (a_all.blind_id.isin(expected_ids) & (a_all.label_provenance == "human_independent") & a_all.tone.ne("") & ~a_all.tone.isin(VALID_TONES)).sum()
        + (b_all.blind_id.isin(expected_ids) & (b_all.label_provenance == "human_independent") & b_all.tone.ne("") & ~b_all.tone.isin(VALID_TONES)).sum()
    )
    paired = a[["blind_id", "tone"]].merge(b[["blind_id", "tone"]], on="blind_id", suffixes=("_a", "_b"))
    OUT.mkdir(parents=True, exist_ok=True)
    paired.to_csv(OUT / "paired_historical_extension_human_tone_labels.csv", index=False)
    complete = len(paired) == len(expected_ids) == 60 and not invalid_tones
    summary = {"paired_human_labels": int(len(paired)), "raw_tone_agreement": None if not len(paired) else round(float((paired.tone_a == paired.tone_b).mean()), 3), "cohen_kappa": kappa(paired.tone_a, paired.tone_b), "required_paired_labels": 60, "invalid_tone_rows": invalid_tones, "ignored_nonpacket_rows": extra_rows, "gate_passed": complete, "message": "Extension label-count gate passed; adjudicate tone disagreements." if complete else "Blocked: all 60 extension rows require paired independent human labels with valid tone values."}
    (OUT / "historical_extension_label_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
