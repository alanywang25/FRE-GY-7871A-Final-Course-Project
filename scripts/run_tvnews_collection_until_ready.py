"""Run resumable TV News Archive collection batches until 60 monthly rows exist.

The underlying collector checkpoints every few source-month tasks.  This runner
then rebuilds the availability-dated monthly series and stops immediately when
the documented 60-month gate is met (or when the configured batch limit is
reached).  It never marks model eligibility: independent-label validation is a
separate required step.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "scripts" / "collect_internet_archive_tvnews_historical.py"
BUILDER = ROOT / "scripts" / "build_historical_media_monthly.py"
STATUS = ROOT / "data" / "corpus" / "historical" / "processed" / "historical_series_status.json"


def read_status() -> dict:
    return json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-tasks", type=int, default=8)
    parser.add_argument("--max-batches", type=int, default=60)
    args = parser.parse_args()
    for batch in range(1, args.max_batches + 1):
        subprocess.run([sys.executable, str(COLLECTOR), "--max-tasks", str(args.batch_tasks)], check=True)
        subprocess.run([sys.executable, str(BUILDER)], check=True)
        status = read_status()
        print(json.dumps({"batch": batch, "monthly_rows": status.get("monthly_rows"), "ready": status.get("ready"), "coverage": status.get("coverage")}, sort_keys=True), flush=True)
        if status.get("ready"):
            return
    raise SystemExit("Stopped at --max-batches before reaching the 60-month gate; rerun to continue.")


if __name__ == "__main__":
    main()
