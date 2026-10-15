"""Ingest publisher-supplied legacy three-component EPU and NAR HAI snapshots.

This script intentionally updates only the *current-vintage* control panel.
It does not make a historical real-time claim: the supplied EPU workbook is a
current monthly history, while the NAR release is a current September 2026
release that revises recent values.  The ALFRED/primary-release vintage gate
continues to govern historical forecast evaluation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "external" / "raw"
PROCESSED = ROOT / "data" / "external" / "processed"
CONTROLS = PROCESSED / "public_macro_controls.csv"
MANIFEST = PROCESSED / "refresh_manifest.json"
NAR_URL = "https://www.nar.realtor/sites/default/files/2026-10/hai-09-2026-housing-affordability-index-2026-10-13.pdf"
EPU_URL = "https://www.policyuncertainty.com/us_monthly.html"

# Transcribed only from the national, fixed-rate HAI column in the cited
# 2026-10-13 NAR release.  "r" and "p" are retained rather than hidden.
NAR_HAI = [
    ("2025-09-01", 106.7, "final"), ("2025-10-01", 107.3, "final"),
    ("2025-11-01", 109.1, "final"), ("2025-12-01", 111.4, "final"),
    ("2026-01-01", 116.6, "final"), ("2026-02-01", 116.5, "final"),
    ("2026-03-01", 112.5, "final"), ("2026-04-01", 108.6, "final"),
    ("2026-05-01", 104.6, "final"), ("2026-06-01", 101.4, "final"),
    ("2026-07-01", 102.7, "final"), ("2026-08-01", 103.7, "revised"),
    ("2026-09-01", 105.4, "preliminary"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def month_end(year: pd.Series, month: pd.Series) -> pd.Series:
    return pd.to_datetime(dict(year=year.astype(int), month=month.astype(int), day=1)) + pd.offsets.MonthEnd(0)


def load_epu(path: Path) -> pd.DataFrame:
    # USEPUINDXM is the monthly three-component EPU index.  Using this sheet
    # makes the current source definition consistent with the ALFRED archive.
    frame = pd.read_excel(path, sheet_name="Legacy Three Component EPU")
    frame = frame.rename(columns={"Three_Component_Index": "policy_uncertainty"})
    frame["Year"] = pd.to_numeric(frame["Year"], errors="coerce")
    frame["Month"] = pd.to_numeric(frame["Month"], errors="coerce")
    frame["policy_uncertainty"] = pd.to_numeric(frame["policy_uncertainty"], errors="coerce")
    frame = frame.loc[frame["Year"].notna() & frame["Month"].between(1, 12) & frame["policy_uncertainty"].notna()].copy()
    frame["month"] = month_end(frame["Year"], frame["Month"])
    return frame[["month", "policy_uncertainty"]].sort_values("month").drop_duplicates("month", keep="last")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epu-xlsx", type=Path, required=True, help="Publisher's US Policy Uncertainty Data workbook")
    args = parser.parse_args()
    if not args.epu_xlsx.exists():
        raise FileNotFoundError(args.epu_xlsx)
    if not CONTROLS.exists() or not MANIFEST.exists():
        raise FileNotFoundError("Run scripts/refresh_public_macro.py before this importer.")

    RAW.mkdir(parents=True, exist_ok=True)
    epu = load_epu(args.epu_xlsx)
    retrieved = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    epu_raw = RAW / f"US_Policy_Uncertainty_Data_{retrieved[:10]}.csv"
    epu.assign(observation_date=epu["month"].dt.strftime("%Y-%m-%d"))[["observation_date", "policy_uncertainty"]].to_csv(epu_raw, index=False)

    hai = pd.DataFrame(NAR_HAI, columns=["observation_date", "housing_affordability", "release_status"])
    hai["release_date"] = "2026-10-13"
    hai["source_url"] = NAR_URL
    hai_raw = RAW / "FIXHAI_2026-10-13_nar_release.csv"
    hai.to_csv(hai_raw, index=False)
    hai["month"] = pd.to_datetime(hai["observation_date"]) + pd.offsets.MonthEnd(0)

    controls = pd.read_csv(CONTROLS, parse_dates=["month"])
    controls["month"] = controls["month"] + pd.offsets.MonthEnd(0)
    controls = controls.merge(epu.rename(columns={"policy_uncertainty": "publisher_epu"}), on="month", how="left")
    controls["policy_uncertainty"] = controls["publisher_epu"].combine_first(controls.get("policy_uncertainty"))
    controls = controls.drop(columns="publisher_epu")
    controls = controls.merge(hai[["month", "housing_affordability"]].rename(columns={"housing_affordability": "nar_hai"}), on="month", how="left")
    controls["housing_affordability"] = controls["nar_hai"].combine_first(controls.get("housing_affordability"))
    controls = controls.drop(columns="nar_hai").sort_values("month")
    controls.to_csv(CONTROLS, index=False)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # Replace the previous daily FRED-mirror registry entry so the current
    # panel and the archived panel identify the same monthly EPU definition.
    epu_entry = {
        "variable": "policy_uncertainty",
        "fred_series": "USEPUINDXM",
        "request_url": "https://fred.stlouisfed.org/series/USEPUINDXM",
        "raw_file": str(epu_raw.relative_to(ROOT)),
        "sha256": sha256(epu_raw),
        "observations": int(len(epu)),
        "latest_observation": str(epu["month"].max().date()),
        "availability_lag_months": 1,
        "definition": "Legacy three-component monthly U.S. economic policy uncertainty index.",
    }
    manifest["series"] = [entry for entry in manifest.get("series", []) if entry.get("variable") != "policy_uncertainty"] + [epu_entry]
    manifest["supplemental_publisher_inputs"] = {
        "imported_at_utc": retrieved,
        "current_vintage_only": True,
        "policy_uncertainty": {
            "source_url": EPU_URL,
            "source_workbook": args.epu_xlsx.name,
            "source_sha256": sha256(args.epu_xlsx),
            "raw_file": str(epu_raw.relative_to(ROOT)),
            "observations": int(len(epu)),
            "latest_observation": str(epu["month"].max().date()),
            "series_id": "USEPUINDXM",
            "definition": "Legacy three-component U.S. economic policy uncertainty index.",
            "timing_note": "Current publisher history; historical point-in-time values are collected separately from ALFRED.",
        },
        "housing_affordability": {
            "source_url": NAR_URL,
            "raw_file": str(hai_raw.relative_to(ROOT)),
            "observations": int(len(hai)),
            "latest_observation": "2026-09-30",
            "release_status": "September 2026 is preliminary; August 2026 is revised.",
            "timing_note": "Values were transcribed from the dated 2026-10-13 release; they are not a historical release-vintage archive.",
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"epu_rows": len(epu), "epu_latest": str(epu["month"].max().date()), "hai_rows": len(hai), "hai_latest": "2026-09-30", "controls": str(CONTROLS.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
