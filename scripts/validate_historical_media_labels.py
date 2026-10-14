"""Evaluate paired historical independent labels; excludes machine labels."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "data/corpus/historical/independent_validation"
OUT = ROOT / "data/corpus/historical/validation"

def packet(name: str) -> pd.DataFrame:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            frame = pd.read_csv(PACKETS / name, dtype=str, encoding=encoding).fillna("")
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("unknown", b"", 0, 0, f"Cannot decode {name}")
    frame = frame.loc[(frame.label_provenance == "human_independent") & frame.tone.ne("")]
    return frame[["blind_id", "tone"]].rename(columns={"tone": f"tone_{name[-5]}"})

def kappa(a: pd.Series, b: pd.Series):
    labels = sorted(set(a) | set(b)); observed = float((a == b).mean()) if len(a) else 0
    expected = sum(float((a == label).mean() * (b == label).mean()) for label in labels)
    return None if not len(a) or np.isclose(1 - expected, 0) else round((observed - expected) / (1 - expected), 3)

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paired = packet("annotator_a.csv").merge(packet("annotator_b.csv"), on="blind_id")
    paired["agree"] = paired.tone_a == paired.tone_b
    paired.to_csv(OUT / "paired_historical_human_tone_labels.csv", index=False)
    n = len(paired); agreement = round(float(paired.agree.mean()), 3) if n else None
    summary = {"paired_human_labels": n, "raw_tone_agreement": agreement, "cohen_kappa": kappa(paired.tone_a, paired.tone_b), "minimum_paired_labels": 60, "gate_passed": n >= 60, "message": "Historical label-count gate passed; adjudicate tone disagreements before classifier validation." if n >= 60 else "Blocked: fewer than 60 paired independent historical labels."}
    (OUT / "historical_label_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__": main()
