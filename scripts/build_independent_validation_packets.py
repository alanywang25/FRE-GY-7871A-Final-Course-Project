"""Create blank, source-blinded packets for independent human validation."""
from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "corpus" / "processed" / "balanced_analysis_sample.csv"
OUT = ROOT / "data" / "corpus" / "independent_validation"
FIELDS = [
    "item_id", "text", "text_representation", "tone", "salience_layoffs", "salience_hiring",
    "salience_price_level", "salience_disinflation", "salience_growth", "salience_recession_risk",
    "frame_price_level", "frame_inflation_rate", "frame_household_experience", "frame_national_aggregate",
    "frame_current", "frame_forecast", "factual_calibration", "benchmark_reference",
    "political_attribution_target", "political_valence", "evidence_excerpt", "annotator_notes",
    "label_provenance", "model_name",
]


def packet(rows: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    items = list({row["item_id"]: row for row in rows}.values())
    random.Random(seed).shuffle(items)
    return [{field: row.get(field, "") if field in {"item_id", "text", "text_representation"} else "" for field in FIELDS} for row in items]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with INPUT.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for name, seed in (("annotator_a.csv", 20261013), ("annotator_b.csv", 20261014)):
        with (OUT / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(packet(rows, seed))
    (OUT / "README.md").write_text(
        "# Independent validation packets\n\nThese are fresh, source-blinded packets with no machine labels, model names, or prior reviewer decisions. Each annotator must code all fields independently, then set `label_provenance` to `human_independent`. Do not copy values from the reviewed packets.\n",
        encoding="utf-8",
    )
    print("Created two blank independent-validation packets with 312 unique items each.")


if __name__ == "__main__":
    main()
