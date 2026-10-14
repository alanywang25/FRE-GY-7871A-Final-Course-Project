# Historical independent validation

Both annotators independently code every row, without source, date, URL, dictionary outputs, or prior labels. Enter `human_independent` in `label_provenance` only after a human has coded the row. Do not edit the blind-key file or use it during annotation.

After both packets are complete, run:

```sh
python scripts/validate_historical_media_labels.py
python scripts/build_historical_tone_adjudication.py
```

Resolve only the rows in `adjudication/historical_tone_adjudication_queue.csv`, then rerun the adjudication builder followed by:

```sh
python scripts/validate_historical_classifier_against_adjudication.py
```

The historical monthly series remains pending independent-label validation until this workflow has been reviewed.
