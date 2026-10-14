# Historical-extension independent validation

Both annotators independently code every row without source, date, URL, archive ID, dictionary output, or the other annotator's labels. Use `negative`, `mixed`, `neutral`, or `positive` for `tone`. Use `human_independent` in `label_provenance` only after a person has completed the row. The two annotators must not compare packets or labels before both files are finished. Do not edit `validation_internal/historical_extension_blind_key.csv`.

After both packets are complete, run:

```sh
python scripts/validate_historical_extension_labels.py
python scripts/build_historical_extension_tone_adjudication.py
```

For each remaining disagreement in `adjudication/extension_tone_decisions.csv`, enter the selected final `adjudicated_tone`, an `adjudicator` identifier, the date, and a concise rationale. Then rerun the adjudication builder and:

```sh
python scripts/build_historical_media_monthly.py
python scripts/build_media_model_analysis.py
```

The historical model stays blocked until all 60 paired labels are present and every tone disagreement is resolved. Keep the internal blind key private until annotation and adjudication are complete.
