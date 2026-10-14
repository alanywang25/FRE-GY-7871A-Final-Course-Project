"""Build chronological media-model comparisons when aligned history is sufficient.

This script deliberately writes a blocked status rather than fitting an
underpowered model. It uses only media values whose item-level aggregate was
available by the forecast month and evaluates untouched chronological holdouts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.pipeline import diagnostics, load_macro_data, model_metrics, rolling_ols_forecast

HISTORICAL_MEDIA = ROOT / "data/corpus/historical/processed/historical_media_monthly.csv"
HISTORICAL_STATUS = ROOT / "data/corpus/historical/processed/historical_series_status.json"
OUT = ROOT / "data/processed"
STATUS = OUT / "media_model_status.json"
PANEL_OUT = OUT / "historical_media_model_panel.csv"
RESULTS_OUT = OUT / "historical_media_model_oos.csv"
MIN_ALIGNED_MONTHS = 84  # 48-month initial training window plus 36 OOS forecasts.
# The historical archive's independent validation/adjudication establishes
# tone only. Keep other archived coding dimensions descriptive until they
# receive their own all-field validation.
MEDIA_FEATURES = ["tone_negative_share"]
LAGGED_MEDIA_FEATURES = [f"media_{feature}" for feature in MEDIA_FEATURES]
BASELINE_FEATURES = ["unemployment", "pce_yoy", "gdp_qoq_annualized"]


def write_status(status: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))


def lag_media(media: pd.DataFrame, lag: int) -> pd.DataFrame:
    columns = ["month", "available_on", *MEDIA_FEATURES]
    result = media[columns].copy().sort_values("month")
    if lag:
        result[MEDIA_FEATURES] = result[MEDIA_FEATURES].shift(lag)
        result["available_on"] = result["available_on"].shift(lag)
    return result.rename(columns={column: f"media_{column}" for column in MEDIA_FEATURES + ["available_on"]})


def coefficient_summary(results: pd.DataFrame, features: list[str]) -> dict:
    """Summarize rolling coefficients saved by the forecast helper when present."""
    summary = {}
    for feature in features:
        column = f"coef_{feature}"
        if column not in results:
            continue
        values = pd.to_numeric(results[column], errors="coerce").dropna()
        if len(values):
            summary[feature] = {"n": int(len(values)), "mean": round(float(values.mean()), 4), "std": round(float(values.std(ddof=0)), 4), "min": round(float(values.min()), 4), "max": round(float(values.max()), 4)}
    return summary


def main() -> None:
    if not HISTORICAL_MEDIA.exists() or not HISTORICAL_STATUS.exists():
        write_status({"ready": False, "estimated": False, "reason": "Historical availability-dated media series is missing."})
        return
    historical = json.loads(HISTORICAL_STATUS.read_text(encoding="utf-8"))
    if not historical.get("ready") or not historical.get("independent_validation_complete", False):
        write_status({"ready": False, "estimated": False, "reason": historical.get("independent_validation_message", "Historical media series has not passed its input/readiness checks.")})
        return

    media = pd.read_csv(HISTORICAL_MEDIA, parse_dates=["month", "available_on"])
    # CSV timestamps are UTC while the monthly macro panel is timezone-naive.
    media["available_on"] = pd.to_datetime(media["available_on"], utc=True).dt.tz_convert(None)
    macro = load_macro_data().loc[lambda x: x["month"] >= "2010-01-31"].copy()
    panels = {}
    for lag in (0, 1):
        candidate = macro.merge(lag_media(media, lag), on="month", how="inner")
        candidate = candidate.loc[candidate["media_available_on"] <= candidate["month"] + pd.offsets.MonthEnd(0)].copy()
        panels[lag] = candidate
    aligned = panels[1]
    PANEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    aligned.to_csv(PANEL_OUT, index=False)
    if len(aligned) < MIN_ALIGNED_MONTHS:
        write_status({
            "ready": False, "estimated": False,
            "reason": "Insufficient aligned, availability-dated history for a meaningful chronological media comparison.",
            "aligned_months": int(len(aligned)), "minimum_aligned_months": MIN_ALIGNED_MONTHS,
            "coverage": {"first_month": None if aligned.empty else str(aligned.month.min().date()), "last_month": None if aligned.empty else str(aligned.month.max().date())},
            "required_next_step": "Extend the coded historical archive while preserving availability timestamps; at least 84 aligned months are required for the configured 48-month initial training window and 36 OOS forecasts.",
            "measurement_scope": "Historical independent validation adjudicates tone. The fitted historical specification therefore uses tone only.",
        })
        return

    # Pre-specified one-month lag is primary; contemporaneous media is sensitivity only.
    primary = aligned.copy()
    primary["month_sin"] = np.sin(2 * np.pi * primary.month.dt.month / 12)
    primary["month_cos"] = np.cos(2 * np.pi * primary.month.dt.month / 12)
    seasonal = ["month_sin", "month_cos"]
    specs = {
        "economic_only": BASELINE_FEATURES + seasonal,
        "economic_plus_media": BASELINE_FEATURES + LAGGED_MEDIA_FEATURES + seasonal,
    }
    fitted = {name: rolling_ols_forecast(primary, features, training_window=48, min_train=48) for name, features in specs.items()}
    sensitivity = {}
    for lag, candidate in panels.items():
        candidate = candidate.copy()
        candidate["month_sin"] = np.sin(2 * np.pi * candidate.month.dt.month / 12)
        candidate["month_cos"] = np.cos(2 * np.pi * candidate.month.dt.month / 12)
        if len(candidate) >= MIN_ALIGNED_MONTHS:
            result = rolling_ols_forecast(candidate, specs["economic_plus_media"], training_window=48, min_train=48)
            sensitivity[f"media_lag_{lag}"] = model_metrics(result)

    combined = primary[["month"]].copy()
    for name, result in fitted.items():
        keep = result[["month", "sentiment", "prediction", "sentiment_gap", "prediction_lower_95", "prediction_upper_95"]].copy()
        keep = keep.rename(columns={column: f"{name}_{column}" for column in keep.columns if column != "month"})
        combined = combined.merge(keep, on="month", how="left")
    combined.to_csv(RESULTS_OUT, index=False)
    write_status({
        "ready": True, "estimated": True, "primary_media_lag_months": 1,
        "aligned_months": int(len(primary)), "minimum_aligned_months": MIN_ALIGNED_MONTHS,
        "coverage": {"first_month": str(primary.month.min().date()), "last_month": str(primary.month.max().date())},
        "models": {name: {**model_metrics(result), "diagnostics": diagnostics(result), "coefficient_stability": coefficient_summary(result, specs[name])} for name, result in fitted.items()},
        "lag_sensitivity": sensitivity,
        "measurement_scope": "Historical specification uses independently validated tone only; framing, salience, and factual calibration remain descriptive in the archive.",
        "caveats": ["Forecast improvement is associational, not causal.", "Seasonal sine/cosine terms are included; residual autocorrelation is reported.", "Do not report media-dimension effects beyond independently validated tone."],
    })


if __name__ == "__main__":
    main()
