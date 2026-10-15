"""Create blinded, independently ordered coding packets for two annotators."""
from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "corpus" / "processed" / "balanced_analysis_sample.csv"
OUT = ROOT / "data" / "corpus" / "labeling"
LABEL_COLUMNS = [
    "item_id", "text", "text_representation", "tone", "salience_layoffs", "salience_hiring",
    "salience_price_level", "salience_disinflation", "salience_growth", "salience_recession_risk",
    "frame_price_level", "frame_inflation_rate", "frame_household_experience", "frame_national_aggregate",
    "frame_current", "frame_forecast", "factual_calibration", "benchmark_reference",
    "political_attribution_target", "political_valence", "evidence_excerpt", "annotator_notes",
]


def packet(rows: list[dict], seed: int) -> list[dict]:
    rows = rows.copy()
    random.Random(seed).shuffle(rows)
    preserve = {"item_id", "text", "text_representation"}
    return [{column: row.get(column, "") if column in preserve else "" for column in LABEL_COLUMNS} for row in rows]


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=LABEL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    with INPUT.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 300:
        raise ValueError(f"Need at least 300 balanced items, found {len(rows)}")
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "annotator_a.csv", packet(rows, seed=20261012))
    write(OUT / "annotator_b.csv", packet(rows, seed=20261013))
    print(f"Created two blinded packets of {len(rows)} items in {OUT}")


if __name__ == "__main__":
    main()
