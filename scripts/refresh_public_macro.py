"""Fetch public current-vintage macro snapshots and create a dated control panel.

This is deliberately a current-vintage refresh. It records retrieval evidence but
does not pretend to reconstruct historical release-vintage information.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "external" / "series_registry.csv"
RAW = ROOT / "data" / "external" / "raw"
PROCESSED = ROOT / "data" / "external" / "processed"


def fetch_csv(series_id: str) -> tuple[bytes, str]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    with urlopen(url, timeout=45) as response:  # nosec B310: fixed public HTTPS endpoint
        return response.read(), url


def lag_to_available(frame: pd.DataFrame, months: int) -> pd.DataFrame:
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    frame["available_on"] = frame["observation_date"] + pd.offsets.MonthEnd(months)
    return frame


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    registry = pd.read_csv(REGISTRY)
    retrieved = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    snapshots: dict[str, pd.DataFrame] = {}
    manifest: dict[str, object] = {
        "retrieved_at_utc": retrieved,
        "vintage_status": "current revised values only; not an ALFRED historical-vintage panel",
        "series": [],
        "failures": [],
    }
    for row in registry.itertuples(index=False):
        if pd.isna(row.fred_series) or not str(row.fred_series).strip():
            manifest["failures"].append({"variable": row.variable, "error": "direct/licensed source required; no public FRED identifier registered"})
            continue
        try:
            payload, url = fetch_csv(row.fred_series)
            digest = hashlib.sha256(payload).hexdigest()
            destination = RAW / f"{row.fred_series}_{retrieved[:10]}.csv"
            destination.write_bytes(payload)
            frame = pd.read_csv(destination)
            if row.fred_series not in frame or "observation_date" not in frame:
                raise ValueError("FRED response did not contain the requested series column")
            frame = frame.rename(columns={row.fred_series: row.variable})
            frame[row.variable] = pd.to_numeric(frame[row.variable], errors="coerce")
            frame = frame.dropna(subset=[row.variable]).copy()
            lag = 3 if row.frequency == "quarterly" else 1
            snapshots[row.variable] = lag_to_available(frame[["observation_date", row.variable]], lag)
            manifest["series"].append({
                "variable": row.variable, "fred_series": row.fred_series, "request_url": url,
                "raw_file": str(destination.relative_to(ROOT)), "sha256": digest,
                "observations": int(len(frame)), "latest_observation": str(frame["observation_date"].max()),
                "availability_lag_months": lag,
            })
        except Exception as exc:  # retain a machine-readable failure rather than producing silent zeros
            manifest["failures"].append({"variable": row.variable, "fred_series": row.fred_series, "error": str(exc)})

    # Align each series on its own assumed availability date. Quarterly observations
    # are carried forward only after their assumed release date, never interpolated.
    months = pd.DataFrame({"month": pd.date_range("1978-01-31", pd.Timestamp.today().to_period("M").to_timestamp("M"), freq="ME")})
    controls = months.copy()
    for variable, frame in snapshots.items():
        right = frame.rename(columns={"available_on": "available_on_" + variable})
        controls = pd.merge_asof(
            controls.sort_values("month"), right.sort_values("available_on_" + variable),
            left_on="month", right_on="available_on_" + variable, direction="backward"
        ).drop(columns=["observation_date", "available_on_" + variable], errors="ignore")
    if "pce_price_index" in controls:
        controls["pce_yoy_refreshed"] = controls["pce_price_index"].pct_change(12) * 100
        first = controls.loc[controls["month"] >= "2010-01-31", "pce_price_index"].dropna()
        if not first.empty:
            controls["pce_cumulative_since_2010"] = (controls["pce_price_index"] / first.iloc[0] - 1) * 100
    if "real_disposable_income" in controls:
        controls["real_disposable_income_yoy"] = controls["real_disposable_income"].pct_change(12) * 100
    if "real_gdp" in controls:
        controls["real_gdp_qoq_annualized"] = ((controls["real_gdp"] / controls["real_gdp"].shift(3)) ** 4 - 1) * 100
    controls.to_csv(PROCESSED / "public_macro_controls.csv", index=False)
    (PROCESSED / "refresh_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"downloaded": len(snapshots), "failures": manifest["failures"], "retrieved_at_utc": retrieved}, indent=2))


if __name__ == "__main__":
    main()
