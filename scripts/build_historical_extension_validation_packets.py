"""Create blinded independent-label packets for the 2014–2016 archive extension."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/corpus/historical/raw/historical_items.csv"
OUT = ROOT / "data/corpus/historical/supplemental_validation"
INTERNAL = ROOT / "data/corpus/historical/validation_internal"
KEY = INTERNAL / "historical_extension_blind_key.csv"
START, END = pd.Timestamp("2014-01-01", tz="UTC"), pd.Timestamp("2016-06-30 23:59:59", tz="UTC")
FIELDS = ["blind_id", "text", "text_representation", "tone", "salience_layoffs", "salience_hiring", "salience_price_level", "salience_disinflation", "salience_growth", "salience_recession_risk", "frame_price_level", "frame_inflation_rate", "frame_household_experience", "frame_national_aggregate", "frame_current", "frame_forecast", "factual_calibration", "benchmark_reference", "political_attribution_target", "political_valence", "evidence_excerpt", "annotator_notes", "label_provenance", "model_name"]


def main() -> None:
    raw = pd.read_csv(RAW, dtype=str).fillna("")
    raw["published_at"] = pd.to_datetime(raw["published_at"], utc=True)
    eligible = raw.loc[(raw.include_default == "true") & (raw.is_duplicate != "true") & (raw.suspected_automated != "true")].drop_duplicates("item_id").copy()
    sample = eligible.loc[(eligible.published_at >= START) & (eligible.published_at <= END)].sort_values(["published_at", "source_stratum", "item_id"]).reset_index(drop=True)
    if sample.empty:
        raise ValueError("No eligible extension records found.")
    sample["blind_id"] = [f"historical_extension_{number:03d}" for number in range(1, len(sample) + 1)]
    OUT.mkdir(parents=True, exist_ok=True); INTERNAL.mkdir(parents=True, exist_ok=True)
    sample[["blind_id", "item_id", "published_at", "source_domain", "source_stratum"]].to_csv(KEY, index=False)
    for filename, seed in (("annotator_a.csv", 20261017), ("annotator_b.csv", 20261018)):
        ordered = sample.sample(frac=1, random_state=seed)
        rows = [{field: row[field] if field in {"blind_id", "text", "text_representation"} else "" for field in FIELDS} for _, row in ordered.iterrows()]
        with (OUT / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    (OUT / "README.md").write_text("""# Historical-extension independent validation\n\nBoth annotators independently code every row without source, date, URL, archive ID, dictionary output, or the other annotator's labels. Use `human_independent` in `label_provenance` only after a person has completed the row. Do not edit `validation_internal/historical_extension_blind_key.csv`.\n\nAfter both packets are complete, run:\n\n```sh\npython scripts/validate_historical_extension_labels.py\npython scripts/build_historical_extension_tone_adjudication.py\n```\n\nResolve the rows in `adjudication/extension_tone_decisions.csv`, then rerun the adjudication builder and:\n\n```sh\npython scripts/build_historical_media_monthly.py\npython scripts/build_media_model_analysis.py\n```\n""", encoding="utf-8")
    print({"packets": len(sample), "start": str(sample.published_at.min().date()), "end": str(sample.published_at.max().date()), "key": str(KEY)})


if __name__ == "__main__":
    main()
