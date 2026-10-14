"""Create source-blinded, stratified historical-media annotation packets."""
from __future__ import annotations
import csv, random
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/corpus/historical/raw/historical_items.csv"
OUT = ROOT / "data/corpus/historical/independent_validation"
INTERNAL = ROOT / "data/corpus/historical/validation_internal"
FIELDS = ["blind_id", "text", "text_representation", "tone", "salience_layoffs", "salience_hiring", "salience_price_level", "salience_disinflation", "salience_growth", "salience_recession_risk", "frame_price_level", "frame_inflation_rate", "frame_household_experience", "frame_national_aggregate", "frame_current", "frame_forecast", "factual_calibration", "benchmark_reference", "political_attribution_target", "political_valence", "evidence_excerpt", "annotator_notes", "label_provenance", "model_name"]

def main() -> None:
    raw = pd.read_csv(RAW, dtype=str).fillna("")
    raw = raw.loc[(raw.include_default == "true") & (raw.is_duplicate != "true") & (raw.suspected_automated != "true")].drop_duplicates("item_id").copy()
    raw["published_at"] = pd.to_datetime(raw["published_at"], utc=True)
    raw["period_bin"] = pd.qcut(raw["published_at"].astype("int64"), q=4, labels=False, duplicates="drop").astype(str)
    # 10 per source-stratum/time bin = 80 labels, balanced nationally/locally and over time.
    chosen = []
    for _, group in raw.groupby(["source_stratum", "period_bin"], sort=True):
        chosen.append(group.sample(n=min(10, len(group)), random_state=20261013))
    sample = pd.concat(chosen, ignore_index=True).sample(frac=1, random_state=20261014).reset_index(drop=True)
    sample["blind_id"] = [f"historical_validation_{n:03d}" for n in range(1, len(sample) + 1)]
    OUT.mkdir(parents=True, exist_ok=True); INTERNAL.mkdir(parents=True, exist_ok=True)
    sample[["blind_id", "item_id", "published_at", "source_domain", "source_stratum"]].to_csv(INTERNAL / "historical_validation_blind_key.csv", index=False)
    for filename, seed in (("annotator_a.csv", 20261015), ("annotator_b.csv", 20261016)):
        ordered = sample.sample(frac=1, random_state=seed)
        rows = [{field: row[field] if field in {"blind_id", "text", "text_representation"} else "" for field in FIELDS} for _, row in ordered.iterrows()]
        with (OUT / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    (OUT / "README.md").write_text("# Historical independent validation\n\nBoth annotators independently code every row, without source, date, URL, dictionary outputs, or prior labels. Enter `human_independent` in `label_provenance` only after a human has coded the row. Do not edit the blind-key file or use it during annotation.\n", encoding="utf-8")
    print(f"Created {len(sample)} blinded historical items per annotator.")

if __name__ == "__main__": main()
