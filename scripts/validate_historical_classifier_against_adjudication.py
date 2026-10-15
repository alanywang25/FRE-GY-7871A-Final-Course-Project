"""Compare the historical dictionary baseline with finalized independent labels."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from label_corpus_baseline_v3 import label

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/corpus/historical/raw/historical_items.csv"
FINAL = ROOT / "data/corpus/historical/independent_validation/adjudication/historical_tone_adjudications.csv"
OUT = ROOT / "data/corpus/historical/validation"

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not FINAL.exists(): raise FileNotFoundError("Run build_historical_tone_adjudication.py after completing both packets.")
    final = pd.read_csv(FINAL, dtype=str).fillna("")
    final = final.loc[final.adjudication_status.ne("needs_historical_tone_adjudication") & final.adjudicated_tone.ne("")]
    raw = pd.read_csv(RAW, dtype=str).fillna("")
    joined = final.merge(raw[["item_id", "text", "source_stratum"]], on="item_id", how="left")
    joined["predicted_tone"] = [label({"item_id": item, "text": text})["tone"] for item, text in zip(joined.item_id, joined.text_y)]
    joined.rename(columns={"text_x":"text"}, inplace=True)
    joined.to_csv(OUT / "historical_classifier_validation_items.csv", index=False)
    accuracy = float((joined.predicted_tone == joined.adjudicated_tone).mean()) if len(joined) else None
    by_source = joined.groupby("source_stratum").apply(lambda f: pd.Series({"n":len(f), "accuracy":(f.predicted_tone == f.adjudicated_tone).mean()})).reset_index()
    by_source.to_csv(OUT / "historical_classifier_validation_by_stratum.csv", index=False)
    summary={"n":len(joined),"accuracy":None if accuracy is None else round(accuracy,3),"status":"development-set diagnostic; not a held-out generalization estimate","message":"Historical classifier validation requires finalized independent tone adjudications." if not len(joined) else "Historical classifier diagnostic built from finalized independent labels."}
    (OUT / "historical_classifier_validation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8"); print(json.dumps(summary,indent=2))

if __name__ == "__main__": main()
