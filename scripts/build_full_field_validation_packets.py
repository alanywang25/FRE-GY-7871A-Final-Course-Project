"""Create a fresh, stratified, source-blinded packet for all-field validation."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/corpus/processed/balanced_analysis_sample.csv"
OUT = ROOT / "data/corpus/full_field_validation"
INTERNAL = ROOT / "data/corpus/validation_internal"
KEY = INTERNAL / "full_field_validation_blind_key.csv"
CODE_FIELDS = [
    "tone", "salience_layoffs", "salience_hiring", "salience_price_level", "salience_disinflation",
    "salience_growth", "salience_recession_risk", "frame_price_level", "frame_inflation_rate",
    "frame_household_experience", "frame_national_aggregate", "frame_current", "frame_forecast",
    "factual_calibration", "political_attribution_target", "political_valence",
]
PACKET_FIELDS = [
    "blind_id", "publication_date", "text", "text_representation", *CODE_FIELDS,
    "benchmark_reference", "evidence_excerpt", "annotator_notes", "label_provenance",
]


def main() -> None:
    source = pd.read_csv(SOURCE, dtype=str).fillna("")
    source = source.drop_duplicates("item_id", keep="first")
    strata = ("national", "local", "social")
    selected = []
    for stratum in strata:
        group = source.loc[source.source_stratum.eq(stratum)].sort_values(["published_at", "item_id"])
        if len(group) < 100:
            raise ValueError(f"{stratum} has only {len(group)} unique items; at least 100 are required.")
        selected.append(group)
    sample = pd.concat(selected, ignore_index=True)
    if len(sample) < 300:
        raise ValueError("The stratified validation sample must contain at least 300 items.")
    sample = sample.sort_values(["source_stratum", "published_at", "item_id"]).reset_index(drop=True)
    sample["blind_id"] = [f"full_field_{number:03d}" for number in range(1, len(sample) + 1)]
    # Reserve 20 items per source stratum for a one-time final model claim.
    sample["evaluation_split"] = "development"
    for stratum in strata:
        ids = sample.loc[sample.source_stratum.eq(stratum), "blind_id"].sample(n=20, random_state=20261019).tolist()
        sample.loc[sample.blind_id.isin(ids), "evaluation_split"] = "held_out"

    OUT.mkdir(parents=True, exist_ok=True)
    INTERNAL.mkdir(parents=True, exist_ok=True)
    sample[["blind_id", "item_id", "published_at", "source_domain", "source_stratum", "evaluation_split"]].to_csv(KEY, index=False)
    for filename, seed in (("annotator_a.csv", 20261020), ("annotator_b.csv", 20261021)):
        ordered = sample.sample(frac=1, random_state=seed)
        rows = []
        for _, row in ordered.iterrows():
            packet = {field: "" for field in PACKET_FIELDS}
            packet.update({"blind_id": row["blind_id"], "publication_date": row["published_at"][:10], "text": row["text"], "text_representation": row["text_representation"]})
            rows.append(packet)
        with (OUT / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=PACKET_FIELDS)
            writer.writeheader(); writer.writerows(rows)
    (OUT / "README.md").write_text(
        """# Source-blinded all-field validation\n\nEach reviewer independently codes all 312 records. The packet withholds outlet, URL, source stratum, prior labels, and model output. Publication date is included only to support release-time factual checking.\n\nUse: tone = `negative`, `neutral`, `mixed`, or `positive`; salience/frame fields = `0` or `1`; factual calibration = `calibrated`, `materially incomplete-or-misleading`, or `unverifiable`; political attribution target = a compact target or `none`; political valence = `credit`, `blame`, `neutral`, or `none` (use `none` exactly when the target is `none`).\n\nFor each numerical claim, compare against the official release available on the publication date. Record a compact official `benchmark_reference` and an `evidence_excerpt`; use `unverifiable` only where no official matching evidence is available. Set `label_provenance` to `human_independent` only after the entire row is complete. Do not use the private blind key or discuss labels before both packets are complete.\n\nAfter labeling run:\n\n```sh\npython scripts/validate_full_field_labels.py\npython scripts/build_full_field_adjudication.py\n```\n\nResolve every row in `adjudication/full_field_decisions.csv` with a named adjudicator, date, rationale, evidence excerpt, and benchmark reference. Then rerun the adjudication builder and run `python scripts/evaluate_full_field_model.py`. The 60 held-out records are reserved for the final, one-time model-performance claim.\n""",
        encoding="utf-8",
    )
    print({"sample_rows": len(sample), "by_stratum": sample.source_stratum.value_counts().to_dict(), "held_out": int(sample.evaluation_split.eq("held_out").sum()), "key": str(KEY)})


if __name__ == "__main__":
    main()
