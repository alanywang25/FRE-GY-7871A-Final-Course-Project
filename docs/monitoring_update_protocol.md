# Pre-election monitoring update protocol

The current dated cutoff is **2026-10-14**. October media observations are
partial until their calendar month ends and are displayed at the cutoff date,
not as a completed October month.

For every refresh through election day:

1. Add only retained, availability-dated media items and rerun the applicable
   labeling/adjudication gate before aggregating new measures.
2. Refresh ALFRED and publisher inputs; preserve raw responses, vintage IDs,
   release dates, and hashes.
3. Add a row to `data/templates/major_events.csv` only for a documented event
   relevant to interpretation. Leave the file blank rather than inventing an
   event chronology.
4. Run `scripts/build_media_model_analysis.py`, `src/pipeline.py`, and
   `scripts/build_notebook.py`; archive the resulting dashboard payload and
   model status with the update date.

The dashboard is descriptive between refreshes. No incomplete month is treated
as a complete monthly observation, and no release date is interpreted as a
known intraday ordering.
