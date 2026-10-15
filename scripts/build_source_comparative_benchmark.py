"""Build a transparent, source-comparative media benchmark.

The benchmark matches coded items by publication day and a pre-specified
economic-topic signature (the six salience flags).  Within each matched cell it
compares source strata, rather than treating the entire convenience corpus as
an exposure-weighted population.  It is evidence about differences in retained
content supply, not proof of ideological bias or audience exposure.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data/corpus/full_field_validation/adjudication/full_field_adjudicated_labels.csv"
OUT = ROOT / "data/processed/source_comparative_benchmark.csv"
SUMMARY = ROOT / "data/processed/source_comparative_benchmark_status.json"

TOPIC_FIELDS = [
    "salience_layoffs", "salience_hiring", "salience_price_level",
    "salience_disinflation", "salience_growth", "salience_recession_risk",
]
MEASURES = {
    "negative_tone": lambda x: x["tone"].eq("negative").astype(float),
    "positive_tone": lambda x: x["tone"].eq("positive").astype(float),
    "price_level_frame": lambda x: x["frame_price_level"].eq("1").astype(float),
    "household_experience_frame": lambda x: x["frame_household_experience"].eq("1").astype(float),
    "recession_risk_salience": lambda x: x["salience_recession_risk"].eq("1").astype(float),
    "materially_incomplete_calibration": lambda x: x["factual_calibration"].eq("materially incomplete-or-misleading").astype(float),
    "political_attribution": lambda x: x["political_attribution_target"].ne("none").astype(float),
}


def main() -> None:
    gold = pd.read_csv(GOLD, dtype=str).fillna("")
    required = {"publication_date", "source_stratum", "tone", "factual_calibration", "political_attribution_target", *TOPIC_FIELDS}
    missing = sorted(required - set(gold))
    if missing:
        raise ValueError(f"Missing required adjudicated-label fields: {missing}")
    gold["publication_date"] = pd.to_datetime(gold["publication_date"], errors="raise").dt.date.astype(str)
    gold["topic_signature"] = gold[TOPIC_FIELDS].astype(str).agg("".join, axis=1)
    gold["match_cell"] = gold["publication_date"] + "|" + gold["topic_signature"]
    for name, function in MEASURES.items():
        gold[name] = function(gold)

    cell_counts = gold.groupby("match_cell")["source_stratum"].nunique()
    matched = gold.loc[gold["match_cell"].isin(cell_counts[cell_counts >= 2].index)].copy()
    rows = []
    strata = sorted(matched["source_stratum"].unique())
    for measure in MEASURES:
        cell_means = matched.pivot_table(index="match_cell", columns="source_stratum", values=measure, aggfunc="mean")
        for source_a, source_b in itertools.combinations(strata, 2):
            if source_a not in cell_means or source_b not in cell_means:
                continue
            paired = cell_means[[source_a, source_b]].dropna()
            diff = paired[source_b] - paired[source_a]
            n = len(diff)
            se = float(diff.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
            average = float(diff.mean()) if n else float("nan")
            rows.append({
                "measure": measure,
                "source_a": source_a,
                "source_b": source_b,
                "matched_day_topic_cells": n,
                "source_a_mean": round(float(paired[source_a].mean()), 6) if n else float("nan"),
                "source_b_mean": round(float(paired[source_b].mean()), 6) if n else float("nan"),
                "difference_b_minus_a": round(average, 6),
                "difference_pp_b_minus_a": round(100 * average, 2),
                "normal_approx_ci_low_pp": round(100 * (average - 1.96 * se), 2) if n > 1 else float("nan"),
                "normal_approx_ci_high_pp": round(100 * (average + 1.96 * se), 2) if n > 1 else float("nan"),
                "interpretation": "Matched publication-day/topic content-supply contrast; not an exposure or causal estimate.",
            })
    result = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    summary = {
        "ready": not result.empty,
        "items": int(len(gold)),
        "matched_items": int(len(matched)),
        "matched_day_topic_cells": int(cell_counts[cell_counts >= 2].size),
        "comparisons": int(len(result)),
        "method": "Pairs source strata within publication-day and pre-specified salience-topic cells; reports unweighted matched-cell contrasts.",
        "scope": "Content supply only. This benchmark does not establish bias, represent audience exposure, or identify causal effects.",
        "output": str(OUT.relative_to(ROOT)),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
