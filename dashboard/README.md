# Monitoring dashboard

The dashboard is a buildless local website. It reads `data/monitoring_payload.json`, produced by `src/pipeline.py`.

```bash
python ../src/pipeline.py --cutoff 2026-10-14
python -m http.server 8000
```

Then visit `http://localhost:8000`. A local web server is required because browsers block `fetch()` from a file URL.

The pipeline updates the dashboard payload automatically. The dashboard never fills missing media measures with zeros. The current `data/media_monthly.csv` is a 312-item, source-blinded, all-field validated aggregate; it remains descriptive rather than evidence of exposure or causation. In a genuine pre-election update, replace the availability assumptions in `src/pipeline.py` with release timestamps and vintage values, freeze model versions, and record each update date.

The default cutoff is pinned to the submitted October 14, 2026 snapshot. Supply `--cutoff YYYY-MM-DD` only for a new refresh whose dated inputs and outputs will be archived together.

## How the final deliverables use the dashboard

The dashboard supports the report and presentation as a model-risk monitoring tool. It helps an analyst identify a gap between observed and predicted consumer sentiment, compare forecast variants, review data-quality and availability status, and document the inputs used in a decision. It does not turn media tone into an automatic forecast input.

The completed [written report](../output/report/AI_Economic_Perceptions_Consumer_Sentiment_Report.md) and [presentation](../output/presentation/AI_Economic_Perceptions_Consumer_Sentiment_Presentation.pptx) use the dashboard alongside the reproducible notebook. They interpret the dashboard's media measures as contextual evidence only: the available data do not identify respondent exposure or a causal media effect.
