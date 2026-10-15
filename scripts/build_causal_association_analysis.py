"""Build the project's observational causal-design supplement.

This is intentionally an association analysis, not a causal estimator.  The
available data contain no respondent-level media exposure or exogenous treatment
variation.  It nevertheless makes the descriptive comparison reproducible,
uses a pre-specified lag, controls for observed macro conditions and persistence,
reports HAC uncertainty, and includes a future-media placebo test.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.pipeline import load_macro_data

HISTORICAL_MEDIA = ROOT / "data" / "corpus" / "historical" / "processed" / "historical_media_monthly.csv"
HISTORICAL_STATUS = ROOT / "data" / "corpus" / "historical" / "processed" / "historical_series_status.json"
SUBINDICES = ROOT / "data" / "templates" / "michigan_subindices.csv"
OUT = ROOT / "data" / "processed"
PANEL_OUT = OUT / "causal_association_panel.csv"
RESULTS_OUT = OUT / "causal_association_results.csv"
STATUS_OUT = OUT / "causal_analysis_status.json"

OUTCOMES = {
    "headline_sentiment": "sentiment",
    "current_conditions": "current_conditions",
    "expectations": "expectations",
}
MACRO_CONTROLS = ["unemployment", "pce_yoy", "gdp_qoq_annualized"]
MIN_OBSERVATIONS = 72
HAC_LAGS = 6


def hac_ols(frame: pd.DataFrame, outcome: str, exposure: str, controls: list[str]) -> dict:
    """OLS with a Bartlett-kernel Newey-West covariance matrix.

    A small local implementation avoids a hidden package dependency and keeps the
    covariance definition visible in this reproducible course project.
    """
    columns = [outcome, exposure, *controls]
    data = frame[columns].dropna().copy()
    x = np.column_stack([np.ones(len(data)), data[[exposure, *controls]].to_numpy(float)])
    y = data[outcome].to_numpy(float)
    beta = np.linalg.pinv(x.T @ x) @ x.T @ y
    residual = y - x @ beta
    score = x * residual[:, None]
    meat = score.T @ score
    for lag in range(1, min(HAC_LAGS, len(data) - 1) + 1):
        weight = 1 - lag / (HAC_LAGS + 1)
        gamma = score[lag:].T @ score[:-lag]
        meat += weight * (gamma + gamma.T)
    bread = np.linalg.pinv(x.T @ x)
    covariance = bread @ meat @ bread
    se = np.sqrt(np.clip(np.diag(covariance), 0, None))
    index = 1  # The exposure follows the intercept.
    coefficient = float(beta[index])
    coefficient_se = float(se[index])
    z = coefficient / coefficient_se if coefficient_se else np.nan
    p_value = math.erfc(abs(z) / math.sqrt(2)) if np.isfinite(z) else np.nan
    return {
        "n": int(len(data)),
        "coefficient_per_10pp": coefficient * 0.10,
        "hac_se_per_10pp": coefficient_se * 0.10,
        "ci_low_95_per_10pp": (coefficient - 1.96 * coefficient_se) * 0.10,
        "ci_high_95_per_10pp": (coefficient + 1.96 * coefficient_se) * 0.10,
        "p_value_hac": p_value,
        "r_squared": float(1 - np.sum(residual**2) / np.sum((y - y.mean()) ** 2)),
    }


def build_panel() -> pd.DataFrame:
    macro = load_macro_data().loc[lambda f: f["month"] >= "2010-01-31"].copy()
    subindices = pd.read_csv(SUBINDICES)
    subindices["month"] = pd.to_datetime(subindices["month"], format="mixed").dt.to_period("M").dt.to_timestamp("M")
    subindices["current_conditions"] = pd.to_numeric(subindices["current_conditions"], errors="coerce")
    subindices["expectations"] = pd.to_numeric(subindices["expectations"], errors="coerce")
    subindices["subindex_timing"] = np.where(
        subindices["vintage_id"].fillna("").str.contains("annual-backfill"),
        "annual_backfill_not_realtime", "monthly_final_release",
    )
    media = pd.read_csv(HISTORICAL_MEDIA, parse_dates=["month", "available_on"])
    media["month"] = media["month"].dt.to_period("M").dt.to_timestamp("M")
    media["available_on"] = pd.to_datetime(media["available_on"], utc=True).dt.tz_convert(None)
    media = media.sort_values("month").copy()
    # The primary association is previous-calendar-month negative tone.  The
    # future value is retained solely for a placebo/reverse-timing diagnostic.
    media["negative_tone_lag1"] = media["tone_negative_share"].shift(1)
    media["negative_tone_lead1"] = media["tone_negative_share"].shift(-1)
    media["media_available_by_month_end"] = media["available_on"] <= media["month"] + pd.offsets.MonthEnd(0)
    panel = macro.merge(subindices[["month", "current_conditions", "expectations", "subindex_timing"]], on="month", how="left")
    panel = panel.merge(
        media[["month", "tone_negative_share", "negative_tone_lag1", "negative_tone_lead1", "media_available_by_month_end", "corpus_items", "source_count"]],
        on="month", how="inner",
    )
    panel = panel.loc[panel["media_available_by_month_end"]].sort_values("month").reset_index(drop=True)
    for outcome in OUTCOMES.values():
        panel[f"lag1_{outcome}"] = panel[outcome].shift(1)
    panel["month_sin"] = np.sin(2 * np.pi * panel["month"].dt.month / 12)
    panel["month_cos"] = np.cos(2 * np.pi * panel["month"].dt.month / 12)
    return panel


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not (HISTORICAL_MEDIA.exists() and HISTORICAL_STATUS.exists() and SUBINDICES.exists()):
        status = {"ready": False, "estimated": False, "claim": "not_causal", "reason": "Required historical media, historical readiness, or Michigan subindex input is missing."}
        STATUS_OUT.write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return
    historical_status = json.loads(HISTORICAL_STATUS.read_text(encoding="utf-8"))
    if not historical_status.get("ready") or not historical_status.get("independent_validation_complete"):
        status = {"ready": False, "estimated": False, "claim": "not_causal", "reason": historical_status.get("independent_validation_message", "Historical media validation is incomplete.")}
        STATUS_OUT.write_text(json.dumps(status, indent=2), encoding="utf-8")
        print(json.dumps(status, indent=2))
        return

    panel = build_panel()
    panel.to_csv(PANEL_OUT, index=False)
    controls = [*MACRO_CONTROLS, "month_sin", "month_cos"]
    results = []
    for label, outcome in OUTCOMES.items():
        base_controls = [f"lag1_{outcome}", *controls]
        for specification, exposure in (("primary_lagged_media", "negative_tone_lag1"), ("future_media_placebo", "negative_tone_lead1")):
            estimate = hac_ols(panel, outcome, exposure, base_controls)
            results.append({
                "outcome": label,
                "specification": specification,
                "exposure": exposure,
                **estimate,
                "interpretation": "Association only; not an identified causal effect.",
            })
    results_frame = pd.DataFrame(results)
    results_frame.to_csv(RESULTS_OUT, index=False)
    primary = results_frame.loc[results_frame["specification"].eq("primary_lagged_media")]
    status = {
        "ready": len(panel) >= MIN_OBSERVATIONS,
        "estimated": len(panel) >= MIN_OBSERVATIONS,
        "claim": "associational_not_causal",
        "design": "Retrospective, lagged observational association with macro controls, outcome persistence, calendar seasonality, HAC(6) intervals, and a future-media placebo.",
        "observations": int(len(panel)),
        "coverage": {"first_month": None if panel.empty else str(panel["month"].min().date()), "last_month": None if panel.empty else str(panel["month"].max().date())},
        "primary_exposure": "Previous-calendar-month negative-tone share; coefficients are reported per 10 percentage-point increase.",
        "outcomes": primary[["outcome", "n", "coefficient_per_10pp", "hac_se_per_10pp", "ci_low_95_per_10pp", "ci_high_95_per_10pp", "p_value_hac", "r_squared"]].round(4).to_dict(orient="records"),
        "placebo_test": "Future-month negative tone is included as a reverse-timing placebo; a nonzero placebo is evidence against a simple directional media interpretation, not evidence for causality when null.",
        "subindex_timing": "2010-2025 subindices are annual-report historical backfills. They are valid final-value outcomes for this retrospective association but not a real-time availability claim.",
        "not_identified": [
            "Respondent-level exposure, selection into media consumption, and changes in individual beliefs.",
            "A causal effect of media tone on the national Michigan index.",
            "Confounding by economic shocks, publisher/audience demand, political events, or unmeasured household conditions.",
        ],
        "next_identification_step": "Use the documented randomized truthful-framing experiment with consent, pre-registered outcomes, source-blind stimuli, and required instructor/IRB approval before fielding.",
        "outputs": {"panel": str(PANEL_OUT), "results": str(RESULTS_OUT)},
    }
    STATUS_OUT.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
