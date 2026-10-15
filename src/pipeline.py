"""Reproducible macro baseline and dashboard-data builder.

This module intentionally does not infer media effects when no coded corpus exists.
It creates a chronology-respecting economic-only forecast and exports a small,
portable payload for the local monitoring dashboard.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data" / "raw" / "Perceptual_Bias_Data.xlsx"
DEFAULT_MONITORING_CUTOFF = "2026-10-14"
DEFAULT_MEDIA = ROOT / "data" / "media_monthly.csv"
DEFAULT_CONTROLS = ROOT / "data" / "external" / "processed" / "public_macro_controls.csv"
CONTROL_MANIFEST = ROOT / "data" / "external" / "processed" / "refresh_manifest.json"
LABEL_VALIDATION = ROOT / "data" / "corpus" / "validation" / "label_validation_summary.json"
ADJUDICATION_SUMMARY = ROOT / "data" / "corpus" / "adjudication" / "adjudication_summary.json"
HISTORICAL_MEDIA_STATUS = ROOT / "data" / "corpus" / "historical" / "processed" / "historical_series_status.json"
MEDIA_MODEL_STATUS = ROOT / "data" / "processed" / "media_model_status.json"
EVENT_LOG = ROOT / "data" / "templates" / "release_event_log.csv"
MAJOR_EVENTS = ROOT / "data" / "templates" / "major_events.csv"
SUBGROUP_TEMPLATE = ROOT / "data" / "templates" / "michigan_subgroups.csv"
SUBGROUP_COMPONENT_STATUS = ROOT / "data" / "templates" / "michigan_component_subgroups_status.json"
SUBINDEX_TEMPLATE = ROOT / "data" / "templates" / "michigan_subindices.csv"
VINTAGE_TEMPLATE = ROOT / "data" / "templates" / "macro_vintage_observations.csv"
DICTIONARY_VALIDATION = ROOT / "data" / "corpus" / "validation" / "dictionary_validation_summary.json"
DICTIONARY_INVARIANCE = ROOT / "data" / "corpus" / "validation" / "dictionary_invariance_summary.json"
FULL_FIELD_VALIDATION = ROOT / "data" / "corpus" / "validation" / "full_field_label_validation_summary.json"
FULL_FIELD_ADJUDICATION = ROOT / "data" / "corpus" / "full_field_validation" / "adjudication" / "full_field_adjudication_summary.json"
FULL_FIELD_MODEL = ROOT / "data" / "corpus" / "validation" / "full_field_model_evaluation_summary.json"
CAUSAL_ANALYSIS = ROOT / "data" / "processed" / "causal_analysis_status.json"
SOURCE_BENCHMARK = ROOT / "data" / "processed" / "source_comparative_benchmark_status.json"
SOURCE_BENCHMARK_RESULTS = ROOT / "data" / "processed" / "source_comparative_benchmark.csv"
SOURCE_MONTHLY_MEDIA = ROOT / "data" / "media_monthly_by_source.csv"
PROCESSED = ROOT / "data" / "processed"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
CORPUS_MANIFEST = ROOT / "data" / "corpus" / "processed" / "collection_manifest.json"
ANNOTATION_DIR = ROOT / "data" / "corpus" / "independent_validation"
INDEPENDENT_ADJUDICATION = ANNOTATION_DIR / "adjudication" / "independent_tone_adjudication_summary.json"


def _end_of_month(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).dt.to_period("M").dt.to_timestamp("M")


def load_macro_data(path: Path | str = DEFAULT_RAW) -> pd.DataFrame:
    """Normalize the four side-by-side source series into a monthly panel.

    Availability lags deliberately prevent contemporaneous macro values from
    leaking into a sentiment prediction. They are assumptions to be replaced
    with genuine release timestamps and vintages in a production refresh.
    """
    raw = pd.read_excel(path)
    specs = {
        "unemployment": ("Date", "Unemployment", 1),
        "sentiment": ("Date.1", "Consumer Sentiment", 0),
        "pce_yoy": ("Date.2", "PCE YoY", 2),
        "gdp_qoq_annualized": ("Date.3", "Real GDP QoQ Annualized", 1),
    }
    series: dict[str, pd.DataFrame] = {}
    for name, (date_col, value_col, lag) in specs.items():
        frame = raw[[date_col, value_col]].dropna().copy()
        frame.columns = ["observation_date", name]
        frame["observation_date"] = _end_of_month(frame["observation_date"])
        frame["available_on"] = frame["observation_date"] + pd.offsets.MonthEnd(lag)
        series[name] = frame.sort_values("available_on")

    target = series.pop("sentiment").rename(columns={"observation_date": "month"})
    panel = target[["month", "sentiment"]].sort_values("month").reset_index(drop=True)
    panel["sentiment_available_on"] = panel["month"]

    for name, frame in series.items():
        right = frame[["available_on", name, "observation_date"]].rename(
            columns={"observation_date": f"{name}_observation_date"}
        )
        panel = pd.merge_asof(
            panel.sort_values("month"), right.sort_values("available_on"),
            left_on="month", right_on="available_on", direction="backward"
        ).drop(columns="available_on")

    panel["unemployment_12m_change"] = panel["unemployment"].diff(12)
    panel["recession_signal"] = (panel["gdp_qoq_annualized"] < 0).astype(float)
    return panel.sort_values("month").reset_index(drop=True)


def load_month_end_vintage_macro_panel(raw_path: Path | str = DEFAULT_RAW) -> pd.DataFrame | None:
    """Construct an as-of-final-Michigan-release panel from ALFRED values.

    This is intentionally distinct from the baseline's conservative lag rules.
    It uses documented Michigan final-release dates (date precision) and asks
    which initial-release macro values had appeared by each date.
    """
    if not VINTAGE_TEMPLATE.exists():
        return None
    observations = pd.read_csv(VINTAGE_TEMPLATE, parse_dates=["observation_date", "release_timestamp"])
    required = {"UNRATE", "PCEPI", "GDPC1"}
    if not required.issubset(set(observations["series_id"])):
        return None
    observations["value"] = pd.to_numeric(observations["value"], errors="coerce")
    observations = observations.dropna(subset=["value"]).sort_values(["series_id", "observation_date", "release_timestamp"])
    targets = load_macro_data(raw_path)[["month", "sentiment"]].copy()
    if not SUBINDEX_TEMPLATE.exists():
        return None
    releases = pd.read_csv(SUBINDEX_TEMPLATE, dtype=str)[["month", "release_timestamp"]].copy()
    releases["month"] = pd.to_datetime(releases["month"], format="mixed", errors="coerce")
    releases["release_timestamp"] = pd.to_datetime(releases["release_timestamp"], format="mixed", errors="coerce")
    releases = releases.dropna()
    targets = targets.merge(releases, on="month", how="inner").sort_values("month")
    rows = []
    for target in targets.itertuples(index=False):
        cutoff = pd.Timestamp(target.release_timestamp).normalize()
        available = observations.loc[(observations["release_timestamp"] <= cutoff) & (observations["observation_date"] <= cutoff)]

        def latest(series_id: str) -> pd.Series | None:
            series = available.loc[available["series_id"].eq(series_id)].sort_values(["observation_date", "release_timestamp"])
            return None if series.empty else series.iloc[-1]

        unrate, pce, gdp = (latest(series) for series in ("UNRATE", "PCEPI", "GDPC1"))
        row = {"month": target.month, "sentiment": target.sentiment, "as_of_date": cutoff.date().isoformat(), "sentiment_release_date": cutoff.date().isoformat()}
        if unrate is not None:
            row.update({"unemployment_vintage": unrate.value, "unemployment_observation_date": unrate.observation_date.date().isoformat(), "unemployment_release_date": unrate.release_timestamp.date().isoformat()})
        if pce is not None:
            prior_date = pce.observation_date - pd.DateOffset(months=12)
            prior = available.loc[(available["series_id"].eq("PCEPI")) & (available["observation_date"].eq(prior_date))]
            if not prior.empty:
                prior_value = float(prior.sort_values("release_timestamp").iloc[-1].value)
                row["pce_yoy_vintage"] = 100 * (float(pce.value) / prior_value - 1)
            row.update({"pce_observation_date": pce.observation_date.date().isoformat(), "pce_release_date": pce.release_timestamp.date().isoformat()})
        if gdp is not None:
            prior_date = gdp.observation_date - pd.DateOffset(months=3)
            prior = available.loc[(available["series_id"].eq("GDPC1")) & (available["observation_date"].eq(prior_date))]
            if not prior.empty:
                prior_value = float(prior.sort_values("release_timestamp").iloc[-1].value)
                row["gdp_qoq_annualized_vintage"] = 100 * ((float(gdp.value) / prior_value) ** 4 - 1)
            row.update({"gdp_observation_date": gdp.observation_date.date().isoformat(), "gdp_release_date": gdp.release_timestamp.date().isoformat()})
        rows.append(row)
    return pd.DataFrame(rows).sort_values("month").reset_index(drop=True)


def rolling_ols_forecast(
    panel: pd.DataFrame,
    features: Iterable[str],
    training_window: int = 120,
    min_train: int = 60,
) -> pd.DataFrame:
    """Produce one-step-ahead expanding/rolling OLS predictions without look-ahead."""
    features = list(features)
    cols = ["month", "sentiment", *features]
    model = panel[cols].dropna().sort_values("month").reset_index(drop=True)
    output = model[["month", "sentiment"]].copy()
    output["prediction"] = np.nan
    output["prediction_lower_95"] = np.nan
    output["prediction_upper_95"] = np.nan
    output["training_n"] = np.nan
    output["coef_intercept"] = np.nan
    for feature in features:
        output[f"coef_{feature}"] = np.nan

    for i in range(min_train, len(model)):
        start = max(0, i - training_window)
        train = model.iloc[start:i]
        x_train = np.column_stack([np.ones(len(train)), train[features].to_numpy(float)])
        y_train = train["sentiment"].to_numpy(float)
        beta, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)
        fitted = x_train @ beta
        dof = max(len(train) - x_train.shape[1], 1)
        residual_sd = float(np.sqrt(np.sum((y_train - fitted) ** 2) / dof))
        x_next = np.r_[1.0, model.loc[i, features].to_numpy(float)]
        pred = float(x_next @ beta)
        output.loc[i, ["prediction", "prediction_lower_95", "prediction_upper_95", "training_n"]] = [
            pred, pred - 1.96 * residual_sd, pred + 1.96 * residual_sd, len(train)
        ]
        output.loc[i, "coef_intercept"] = beta[0]
        for feature, value in zip(features, beta[1:]):
            output.loc[i, f"coef_{feature}"] = value

    output["sentiment_gap"] = output["sentiment"] - output["prediction"]
    output["inside_95_interval"] = (
        (output["sentiment"] >= output["prediction_lower_95"])
        & (output["sentiment"] <= output["prediction_upper_95"])
    )
    return output


def model_metrics(results: pd.DataFrame) -> dict[str, float | int | None]:
    test = results.dropna(subset=["prediction"]).copy()
    if test.empty:
        return {"n_oos": 0, "mae": None, "rmse": None, "interval_coverage": None}
    error = test["sentiment"] - test["prediction"]
    return {
        "n_oos": int(len(test)),
        "mae": round(float(np.mean(np.abs(error))), 3),
        "rmse": round(float(np.sqrt(np.mean(error ** 2))), 3),
        "interval_coverage": round(float(test["inside_95_interval"].mean()), 3),
    }


def load_media_monthly(path: Path | str = DEFAULT_MEDIA) -> pd.DataFrame | None:
    path = Path(path)
    if not path.exists():
        return None
    media = pd.read_csv(path, parse_dates=["month"])
    media["month"] = _end_of_month(media["month"])
    return media


def load_public_controls(path: Path | str = DEFAULT_CONTROLS) -> pd.DataFrame | None:
    """Load the separately refreshed current-vintage controls when available."""
    path = Path(path)
    if not path.exists():
        return None
    controls = pd.read_csv(path, parse_dates=["month"])
    controls["month"] = _end_of_month(controls["month"])
    return controls


def _completed_labels(path: Path) -> tuple[int, int, int, int]:
    """Return independent, non-independent, reviewed, and total packet rows."""
    if not path.exists():
        return 0, 0, 0, 0
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            labels = pd.read_csv(path, dtype=str, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise UnicodeDecodeError("unknown", b"", 0, 0, f"Cannot decode {path}")
    labels = labels.fillna("")
    completed = labels["tone"].astype(str).str.strip().ne("")
    provenance = labels.get("label_provenance", pd.Series("", index=labels.index)).astype(str).str.strip()
    human = provenance.eq("human_independent")
    reviewed = provenance.isin(["human_reviewed", "human_reviewed_machine_assisted"])
    machine = provenance.eq("machine_assisted") | reviewed
    return int((completed & human).sum()), int((completed & machine).sum()), int((completed & reviewed).sum()), int(len(labels))


def corpus_status() -> dict:
    """Expose corpus provenance and label readiness for monitoring, not inference."""
    if not CORPUS_MANIFEST.exists():
        return {"available": False, "label_ready": False, "message": "No documented media corpus has been collected.", "balanced_sample_by_stratum": {}, "records_collected": 0, "annotation": {"a_completed": 0, "b_completed": 0, "packet_size": 0}}
    manifest = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8"))
    a_completed, a_machine, a_reviewed, a_size = _completed_labels(ANNOTATION_DIR / "annotator_a.csv")
    b_completed, b_machine, b_reviewed, b_size = _completed_labels(ANNOTATION_DIR / "annotator_b.csv")
    packet_size = min(a_size, b_size)
    label_ready = packet_size >= 300 and a_completed >= 300 and b_completed >= 300
    all_field_ready = False
    if FULL_FIELD_VALIDATION.exists() and FULL_FIELD_ADJUDICATION.exists():
        all_field_ready = bool(
            json.loads(FULL_FIELD_VALIDATION.read_text(encoding="utf-8")).get("gate_passed")
            and json.loads(FULL_FIELD_ADJUDICATION.read_text(encoding="utf-8")).get("gate_passed")
        )
    if all_field_ready:
        message = "Source-blinded all-field independent validation and adjudication are complete; the timestamped aggregate is descriptive, not exposure or causal evidence."
    elif label_ready:
        message = "Independent tone-label packets are complete. Complete all-field validation before treating the aggregate as validated beyond tone."
    else:
        message = f"Human-reviewed labels are complete ({a_reviewed}/{packet_size} for A, {b_reviewed}/{packet_size} for B), but independent blinded tone labels are pending ({a_completed}/{packet_size} for A, {b_completed}/{packet_size} for B). Media measures remain unavailable until independent agreement/adjudication is documented."
    return {"available": True, "label_ready": label_ready, "message": message, "retrieved_at": manifest.get("retrieved_at"), "records_collected": int(manifest.get("records_collected", 0)), "balanced_sample_records": int(manifest.get("balanced_analysis_sample_records", 0)), "balanced_sample_by_stratum": manifest.get("balanced_sample_by_stratum", {}), "annotation": {"a_completed": a_completed, "b_completed": b_completed, "a_machine": a_machine, "b_machine": b_machine, "a_reviewed": a_reviewed, "b_reviewed": b_reviewed, "packet_size": packet_size}}


def validation_status() -> dict:
    if not LABEL_VALIDATION.exists():
        return {"available": False, "gate_passed": False, "message": "Run scripts/validate_media_labels.py after independent human labeling."}
    return json.loads(LABEL_VALIDATION.read_text(encoding="utf-8"))


def _json_status(path: Path, fallback: dict) -> dict:
    """Load an optional workflow status without making dashboard refresh brittle."""
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def macro_refresh_status() -> dict:
    if not CONTROL_MANIFEST.exists():
        return {"available": False, "message": "No public macro refresh has been run. The baseline uses the supplied course workbook."}
    manifest = json.loads(CONTROL_MANIFEST.read_text(encoding="utf-8"))
    coverage = {}
    controls = load_public_controls()
    if controls is not None:
        recent = controls.loc[controls["month"] >= "2010-01-31"]
        coverage = {column: int(recent[column].notna().sum()) for column in recent.columns if column != "month"}
    return {"available": True, "retrieved_at_utc": manifest.get("retrieved_at_utc"), "vintage_status": manifest.get("vintage_status"), "series_downloaded": len(manifest.get("series", [])), "failures": manifest.get("failures", []), "coverage_months_since_2010": coverage}


def diagnostics(results: pd.DataFrame) -> dict[str, float | None]:
    test = results.dropna(subset=["prediction"]).copy()
    if len(test) < 3:
        return {"residual_lag1_autocorrelation": None, "durbin_watson": None}
    residual = (test["sentiment"] - test["prediction"]).to_numpy(float)
    denominator = float(np.sum(residual**2))
    return {
        "residual_lag1_autocorrelation": round(float(pd.Series(residual).autocorr(lag=1)), 3),
        "durbin_watson": round(float(np.sum(np.diff(residual) ** 2) / denominator), 3) if denominator else None,
    }


def template_status(path: Path, required_values: list[str]) -> dict:
    """Expose whether a user has replaced a single example/template row."""
    if not path.exists():
        return {"available": False, "message": f"Missing input contract: {path.name}"}
    frame = pd.read_csv(path, dtype=str).fillna("")
    usable = frame.copy()
    if "notes" in usable:
        usable = usable.loc[~usable["notes"].str.contains("Populate|EXAMPLE", case=False, na=False)]
    complete = bool(len(usable)) and all(usable[column].str.strip().ne("").any() for column in required_values if column in usable)
    return {"available": complete, "rows": int(len(usable)), "message": "Populated input available." if complete else "Template only; supply documented observations before use."}


def subgroup_status() -> dict:
    """Report the loaded ICS table separately from unvalidated ICC/ICE components."""
    status = template_status(
        SUBGROUP_TEMPLATE,
        ["index_value", "sample_size", "release_timestamp", "vintage_id"],
    )
    component = _json_status(
        SUBGROUP_COMPONENT_STATUS,
        {"component_status": "not_loaded", "message": "No component-subgroup availability record found."},
    )
    status["component_status"] = component.get("component_status", "not_loaded")
    status["component_cutoff"] = component.get("last_verified_component_month")
    status["component_missing_months"] = component.get("missing_months", [])
    status["message"] = component.get("message", status["message"])
    return status


def release_events() -> list[dict]:
    if not EVENT_LOG.exists():
        return []
    frame = pd.read_csv(EVENT_LOG, dtype=str).fillna("")
    frame = frame.loc[frame.get("verified_release_timestamp", "").str.casefold().eq("true")]
    # The source log contains compact m/d/yy values. Sort parsed datetimes,
    # rather than strings, so the dashboard genuinely shows the latest events.
    frame["_event_datetime"] = pd.to_datetime(frame["event_date"], format="%m/%d/%y", errors="coerce")
    frame = frame.dropna(subset=["_event_datetime"]).sort_values(["_event_datetime", "series_or_topic"]).tail(36).copy()
    frame["event_date"] = frame["_event_datetime"].dt.strftime("%Y-%m-%d")
    events = frame.drop(columns="_event_datetime")
    if MAJOR_EVENTS.exists():
        major = pd.read_csv(MAJOR_EVENTS, dtype=str).fillna("")
        major = major.loc[major.get("verified", "").str.casefold().eq("true")]
        if not major.empty:
            major = major.rename(columns={"event_date": "event_date", "event_name": "series_or_topic", "source_url": "source_url", "notes": "notes"})
            major["event_type"] = "major_event"
            major["verified_release_timestamp"] = "true"
            events = pd.concat([events, major[events.columns]], ignore_index=True)
    return events.to_dict(orient="records")


def subgroup_records() -> list[dict]:
    """Expose published age-group ICS values without inventing components."""
    if not SUBGROUP_TEMPLATE.exists():
        return []
    frame = pd.read_csv(SUBGROUP_TEMPLATE, dtype=str).fillna("")
    frame = frame.loc[(frame["subgroup_dimension"].eq("age")) & (frame["index_name"].eq("ICS"))]
    if frame.empty:
        return []
    frame["month"] = pd.to_datetime(frame["month"], format="mixed", errors="coerce")
    frame["index_value"] = pd.to_numeric(frame["index_value"], errors="coerce")
    frame = frame.dropna(subset=["month", "index_value"]).sort_values("month")
    return _records(frame, ["month", "subgroup_value", "index_value", "sample_size", "release_timestamp"], limit=600)


def subindex_records() -> list[dict]:
    if not SUBINDEX_TEMPLATE.exists():
        return []
    frame = pd.read_csv(SUBINDEX_TEMPLATE, dtype=str).fillna("")
    for column in ("current_conditions", "expectations"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["month"] = pd.to_datetime(frame["month"], format="mixed", errors="coerce")
    frame = frame.dropna(subset=["month"])
    return _records(frame, ["month", "current_conditions", "expectations", "release_timestamp"], limit=240)


def source_media_records() -> list[dict]:
    if not SOURCE_MONTHLY_MEDIA.exists():
        return []
    frame = pd.read_csv(SOURCE_MONTHLY_MEDIA, parse_dates=["month"])
    return _records(frame, list(frame.columns), limit=180)


def source_benchmark_records() -> list[dict]:
    if not SOURCE_BENCHMARK_RESULTS.exists():
        return []
    frame = pd.read_csv(SOURCE_BENCHMARK_RESULTS)
    # Stable presentation order: most precisely matched contrasts first.
    frame = frame.sort_values(["matched_day_topic_cells", "measure"], ascending=[False, True]).head(6)
    return json.loads(frame.to_json(orient="records"))


def _records(frame: pd.DataFrame, columns: list[str], limit: int = 180) -> list[dict]:
    clean = frame[columns].tail(limit).copy()
    if "month" in clean:
        clean["month"] = pd.to_datetime(clean["month"]).dt.strftime("%Y-%m-%d")
    return json.loads(clean.to_json(orient="records", date_format="iso"))


def build_outputs(
    raw_path: Path | str = DEFAULT_RAW,
    monitoring_cutoff: str | pd.Timestamp = DEFAULT_MONITORING_CUTOFF,
) -> dict:
    """Build deterministic analysis and dashboard artifacts for a dated snapshot.

    ``monitoring_cutoff`` is deliberately explicit rather than inferred from the
    wall clock.  A refresh must choose and archive its own cutoff date.
    """
    PROCESSED.mkdir(parents=True, exist_ok=True)
    panel = load_macro_data(raw_path)
    analysis_panel = panel.loc[panel["month"] >= "2010-01-31"].copy()
    baseline_features = ["unemployment", "pce_yoy", "gdp_qoq_annualized"]
    extension_features = baseline_features + ["unemployment_12m_change", "recession_signal"]
    baseline = rolling_ols_forecast(analysis_panel, baseline_features)
    extension = rolling_ols_forecast(analysis_panel, extension_features)
    dynamic_panel = analysis_panel.copy()
    dynamic_panel["sentiment_lag1"] = dynamic_panel["sentiment"].shift(1)
    dynamic = rolling_ols_forecast(dynamic_panel, baseline_features + ["sentiment_lag1"])
    vintage_panel = load_month_end_vintage_macro_panel(raw_path)
    vintage_model = None
    if vintage_panel is not None:
        vintage_features = ["unemployment_vintage", "pce_yoy_vintage", "gdp_qoq_annualized_vintage"]
        if all(feature in vintage_panel for feature in vintage_features):
            vintage_model = rolling_ols_forecast(vintage_panel.loc[vintage_panel["month"] >= "2010-01-31"], vintage_features)
            vintage_panel.to_csv(PROCESSED / "month_end_vintage_macro_panel.csv", index=False)
    controls = load_public_controls()
    external_extension = None
    if controls is not None:
        enriched = analysis_panel.merge(controls, on="month", how="left", suffixes=("", "_refresh"))
        control_features = [
            "unemployment_u3", "pce_yoy_refreshed", "real_gdp_qoq_annualized",
            "real_disposable_income_yoy", "pce_cumulative_since_2010",
            "debt_service_ratio", "underemployment_u6", "policy_uncertainty",
        ]
        if all(feature in enriched for feature in control_features):
            external_extension = rolling_ols_forecast(enriched, control_features)
            external_extension.to_csv(PROCESSED / "expanded_household_controls_oos.csv", index=False)
    panel.to_csv(PROCESSED / "macro_panel.csv", index=False)
    baseline.to_csv(PROCESSED / "economic_only_oos.csv", index=False)
    extension.to_csv(PROCESSED / "household_stress_extension_oos.csv", index=False)
    dynamic.to_csv(PROCESSED / "dynamic_economic_oos.csv", index=False)
    if vintage_model is not None:
        vintage_model.to_csv(PROCESSED / "month_end_vintage_macro_oos.csv", index=False)

    primary_model = vintage_model if vintage_model is not None else baseline
    primary_panel = vintage_panel if vintage_panel is not None else panel
    cutoff_day = pd.Timestamp(monitoring_cutoff).normalize()
    # Inputs acquired during the cutoff day are eligible; observations dated
    # after that calendar day are not.
    now = cutoff_day + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    latest = panel.loc[panel["month"] <= cutoff_day].dropna(subset=["sentiment"]).sort_values("month").iloc[-1]
    latest_result = primary_model.dropna(subset=["prediction"]).sort_values("month").tail(1)
    media = load_media_monthly()
    if media is not None:
        media["available_on"] = pd.to_datetime(media["available_on"], errors="coerce", utc=True).dt.tz_convert(None)
        media = media.loc[media["available_on"] <= now].copy()
        media["partial_period"] = pd.to_datetime(media["month"]).dt.normalize() > now
        media.loc[media["partial_period"], "month"] = now
    corpus = corpus_status()
    validation = validation_status()
    independent_adjudication = _json_status(INDEPENDENT_ADJUDICATION, {"ready": False, "unresolved": None, "message": "Build the independent tone adjudication queue."})
    refresh = macro_refresh_status()
    adjudication = _json_status(ADJUDICATION_SUMMARY, {"available": False, "message": "Run the adjudication builder."})
    historical_media = _json_status(HISTORICAL_MEDIA_STATUS, {"available": False, "message": "Historical media intake has not been run."})
    media_model = _json_status(MEDIA_MODEL_STATUS, {"ready": False, "estimated": False, "reason": "Run scripts/build_media_model_analysis.py."})
    dictionary_validation = _json_status(DICTIONARY_VALIDATION, {"available": False, "message": "Run classifier validation."})
    dictionary_invariance = _json_status(DICTIONARY_INVARIANCE, {"available": False, "message": "Run the dictionary invariance check."})
    full_field_validation = _json_status(FULL_FIELD_VALIDATION, {"gate_passed": False, "message": "Run all-field independent-label validation."})
    full_field_adjudication = _json_status(FULL_FIELD_ADJUDICATION, {"gate_passed": False, "message": "Run all-field adjudication."})
    full_field_model = _json_status(FULL_FIELD_MODEL, {"ready": False, "message": "Train and evaluate the development-only all-field classifier."})
    causal_analysis = _json_status(CAUSAL_ANALYSIS, {"ready": False, "estimated": False, "claim": "not_causal", "message": "Run scripts/build_causal_association_analysis.py after historical media and subindices are available."})
    source_benchmark = _json_status(SOURCE_BENCHMARK, {"ready": False, "message": "Run scripts/build_source_comparative_benchmark.py."})
    media_has_rows = media is not None and media.dropna(how="all", subset=[c for c in media.columns if c not in {"month", "available_on", "aggregate_status", "notes"}]).shape[0] > 0
    media_independently_adjudicated = bool(
        media_has_rows and "aggregate_status" in media
        and media["aggregate_status"].fillna("").eq("independently_adjudicated").all()
    )
    media_validated = bool(
        media_independently_adjudicated and corpus["label_ready"]
        and full_field_validation.get("gate_passed") and full_field_adjudication.get("gate_passed")
    )
    media_status = {
        "available": media_validated,
        "has_data": media_has_rows,
        "message": corpus["message"] if not media_has_rows else ("Timestamped, independently adjudicated all-field media measures are loaded." if media_validated else "Media measures are present but the all-field independent-label/adjudication gate has not passed."),
    }
    model_comparison = [
        {"name": "Economic-only, release-date ALFRED vintages", "status": "estimated" if vintage_model is not None else "blocked", **(model_metrics(vintage_model) if vintage_model is not None else {"reason": "Populate Michigan final-release dates and ALFRED macro observations."})},
        {"name": "Economic-only, assumed-lag sensitivity", "status": "estimated", **model_metrics(baseline)},
        {"name": "Economic + lagged sentiment (autocorrelation sensitivity)", "status": "estimated", **model_metrics(dynamic)},
        {"name": "Economic + household-stress proxy", "status": "estimated", **model_metrics(extension)},
        {
            "name": "Economic + expanded public controls", "status": "blocked" if external_extension is None else "estimated",
            **({"reason": "Run the public macro refresh and ensure adequate common history."} if external_extension is None else model_metrics(external_extension)),
        },
        {"name": "Economic + historical media", "status": "estimated" if media_model.get("estimated") else "blocked", **(media_model.get("models", {}).get("economic_plus_media", {}) if media_model.get("estimated") else {"reason": media_model.get("reason", "Historical media model has not run.")})},
        {
            "name": "Economic + media + archived household controls",
            "status": "estimated" if media_model.get("third_model", {}).get("estimated") else "blocked",
            **(media_model.get("models", {}).get("economic_media_archived_controls", media_model.get("models", {}).get("economic_media_household_controls_retrospective", {})) if media_model.get("third_model", {}).get("estimated") else {"reason": media_model.get("third_model", {}).get("message", "Requires common historical controls.")}),
        },
    ]
    payload = {
        "metadata": {
            "as_of": str(cutoff_day.date()),
            "model": "Primary: release-date ALFRED-vintage rolling OLS; 120-month window; 95% residual intervals",
            "availability_note": "The primary model joins documented Michigan final-release dates to ALFRED initial-release macro values available by that date. Dates are date-only; intraday ordering is not asserted. Assumed-lag and current-vintage models are sensitivities.",
            "monitoring_cutoff": {"date": str(cutoff_day.date()), "partial_month_policy": "Observations dated after the cutoff are excluded; a current incomplete month is relabeled to the cutoff date and marked partial.", "next_update": "Refresh after each verified Michigan final release and major-event entry through election day; archive inputs, vintages, labels, and outputs on every run."},
            "media_status": media_status,
            "corpus": corpus,
            "label_validation": validation,
            "independent_adjudication": independent_adjudication,
            "adjudication": adjudication,
            "historical_media": historical_media,
            "media_model": media_model,
            "dictionary_validation": dictionary_validation,
            "dictionary_invariance": dictionary_invariance,
            "full_field_validation": full_field_validation,
            "full_field_adjudication": full_field_adjudication,
            "full_field_model": full_field_model,
            "causal_analysis": causal_analysis,
            "source_benchmark": source_benchmark,
            "macro_refresh": refresh,
            "real_time_vintage_note": "The primary ALFRED model uses initial-release values available by each documented Michigan final-release date. Dates are reliable at day precision, not intraday ordering.",
            "input_contracts": {"michigan_subindices": template_status(SUBINDEX_TEMPLATE, ["current_conditions", "expectations", "release_timestamp", "vintage_id"]), "macro_vintages": template_status(VINTAGE_TEMPLATE, ["value", "release_timestamp", "vintage_id"]), "survey_subgroups": subgroup_status()},
        },
        "kpis": {
            "latest_sentiment": round(float(latest["sentiment"]), 1),
            "latest_unemployment": round(float(latest["unemployment"]), 1),
            "latest_pce_yoy": round(float(latest["pce_yoy"]), 2),
            "latest_gdp_qoq_annualized": round(float(latest["gdp_qoq_annualized"]), 1),
            "latest_gap": None if latest_result.empty else round(float(latest_result.iloc[0]["sentiment_gap"]), 2),
        },
        "metrics": {
            "economic_only": model_metrics(primary_model),
            "economic_lagged_sentiment": model_metrics(dynamic),
            "month_end_vintage_macro": None if vintage_model is None else model_metrics(vintage_model),
            "household_stress_proxy": model_metrics(extension),
            "expanded_controls": None if external_extension is None else model_metrics(external_extension),
        },
        "diagnostics": {
            "economic_only": diagnostics(primary_model),
            "economic_lagged_sentiment": diagnostics(dynamic),
            "month_end_vintage_macro": None if vintage_model is None else diagnostics(vintage_model),
            "household_stress_proxy": diagnostics(extension),
            "expanded_controls": None if external_extension is None else diagnostics(external_extension),
        },
        "model_comparison": model_comparison,
        "macro": _records(panel, ["month", "sentiment", "unemployment", "pce_yoy", "gdp_qoq_annualized"]),
        "forecast": _records(primary_model.dropna(subset=["prediction"]), ["month", "sentiment", "prediction", "prediction_lower_95", "prediction_upper_95", "sentiment_gap"]),
        "media": [] if media is None else _records(media, list(media.columns)),
        "media_by_source": source_media_records(),
        "source_benchmark": source_benchmark,
        "source_benchmark_rows": source_benchmark_records(),
        "subgroups": subgroup_records(),
        "subindices": subindex_records(),
        "events": release_events(),
    }
    payload_text = json.dumps(payload, indent=2)
    (PROCESSED / "monitoring_payload.json").write_text(payload_text, encoding="utf-8")
    # Keep the static dashboard refreshable with a single pipeline command.
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    (DASHBOARD_DATA / "monitoring_payload.json").write_text(payload_text, encoding="utf-8")
    (PROCESSED / "run_summary.json").write_text(json.dumps({"metrics": payload["metrics"], "diagnostics": payload["diagnostics"], "macro_refresh": refresh, "label_validation": validation}, indent=2), encoding="utf-8")
    (PROCESSED / "corpus_status.json").write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the dated analysis and dashboard snapshot.")
    parser.add_argument(
        "--cutoff",
        default=DEFAULT_MONITORING_CUTOFF,
        help=f"Snapshot cutoff date in YYYY-MM-DD form (default: {DEFAULT_MONITORING_CUTOFF}).",
    )
    args = parser.parse_args()
    payload = build_outputs(monitoring_cutoff=args.cutoff)
    print(json.dumps({"as_of": payload["metadata"]["as_of"], "metrics": payload["metrics"]}, indent=2))
