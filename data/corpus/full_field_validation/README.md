# Source-blinded all-field validation

Each reviewer independently codes all 312 records. The packet withholds outlet, URL, source stratum, prior labels, and model output. Publication date is included only to support release-time factual checking.

Use: tone = `negative`, `neutral`, `mixed`, or `positive`; salience/frame fields = `0` or `1`; factual calibration = `calibrated`, `materially incomplete-or-misleading`, or `unverifiable`; political attribution target = a compact target or `none`; political valence = `credit`, `blame`, or `neutral`.

For each numerical claim, compare against the official release available on the publication date. Record a compact official `benchmark_reference` and an `evidence_excerpt`; use `unverifiable` only where no official matching evidence is available. Set `label_provenance` to `human_independent` only after the entire row is complete. Do not use the private blind key or discuss labels before both packets are complete.

After labeling run:

```sh
python scripts/validate_full_field_labels.py
python scripts/build_full_field_adjudication.py
```

Resolve every row in `adjudication/full_field_decisions.csv` with a named adjudicator, date, rationale, evidence excerpt, and benchmark reference. Then rerun the adjudication builder and run `python scripts/evaluate_full_field_model.py`. The 60 held-out records are reserved for the final, one-time model-performance claim.
