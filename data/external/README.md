# External macro-data refresh

`scripts/refresh_public_macro.py` downloads public **current-vintage** CSV snapshots from FRED and records the exact request URL, retrieval time, hash, latest observation, and any failures in `data/external/processed/refresh_manifest.json`. It also writes an analysis-ready monthly control panel in `data/external/processed/public_macro_controls.csv`.

Run:

```bash
python scripts/refresh_public_macro.py
python src/pipeline.py
```

The registry identifies the primary publisher even though FRED is used as a reproducible public mirror. It includes headline sentiment, U-3/U-6, PCE price level, real disposable income, real GDP, debt service, housing affordability, and policy uncertainty. Current-conditions and expectations subindices are registered as direct/licensed Michigan inputs: they are intentionally not substituted with a wrong FRED series.

## Timing and vintage guardrail

The downloaded file is revised, current-vintage data. `available_on` is a transparent standard-lag assumption used only to avoid same-month leakage; it is **not** an actual historical release timestamp. The script does not overwrite the supplied course workbook. A real-time backtest must replace these assumptions with an ALFRED/release-calendar vintage panel and archive each vintage used. The dashboard displays this status.

The expanded forecasting specification uses controls with enough common historical coverage. Housing affordability remains in the panel and dashboard as a monitored control, but is excluded from the long historical rolling model when its source history is too short. This is a coverage decision, not a finding about its importance.

## Licensing and redistribution

Only derived values, metadata, and snapshot hashes are intended for the analysis repository. Review the underlying publisher's terms before redistributing raw copies, particularly for Michigan and housing-affordability series. The corpus itself separately retains only permitted metadata/excerpts under its collection protocol.
