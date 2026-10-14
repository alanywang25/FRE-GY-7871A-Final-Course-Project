# Historical media-series intake

Place a licensed or public, item-level coded archive at `raw/historical_items.csv`, then run:

```sh
python scripts/build_historical_media_monthly.py
```

Start a bounded historical collection plan with:

```sh
python scripts/create_historical_collection_plan.py --start 2020-01 --end 2025-12
```

This creates `source_panel.csv`, `collection_plan.csv`, `collection_manifest.json`, and `raw/historical_items_template.csv`. The panel deliberately reproduces national/local domains already represented in the current corpus. It leaves social coverage uncollected until a lawful, documented archive is selected; do not substitute zero-valued social months.

Required columns are `item_id`, `published_at`, `available_on`, `source_domain`, `source_stratum`, `include_default`, `is_duplicate`, `suspected_automated`, `tone`, `frame_price_level`, `salience_recession_risk`, and `factual_calibration`. The source may retain the richer corpus fields as well.

`available_on` must be when the item could actually have been coded and available to the model, not a later reconciliation date. The transformer writes a monthly series and a coverage/status record under `processed/`; it requires at least 60 monthly observations by default, does not fill missing months with zeros, and does not make the result model-eligible until independent-label validation passes. Historical social-platform access may be incomplete, so preserve those gaps and narrow claims accordingly.

For each collected row, retain the archive source, archive record ID, retrieval timestamp, extraction method, and relevant license/terms note in the optional provenance columns included in the template. A retrospective human-labeling date must not be placed in `available_on` for a historical real-time model.
