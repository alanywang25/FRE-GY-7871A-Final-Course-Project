# AI, Economic Perceptions, and Consumer Sentiment

This project implements the complete final-project package: a reproducible analysis, data/corpus/annotation infrastructure, a validation and causal-design package, an updateable monitoring dashboard, a written report, and an eight-slide presentation with a speaker script. It does **not** claim that media bias explains sentiment: forecast improvement is associational, and the project has no respondent-level exposure evidence.

## Final deliverables

The completed report, presentation, and presentation script are available in the output folders:

- [Written report in Markdown](output/report/AI_Economic_Perceptions_Consumer_Sentiment_Report.md) and [PDF](output/report/AI_Economic_Perceptions_Consumer_Sentiment_Report.pdf). The report answers the project research questions, separates hypotheses from findings, includes the reproducible-analysis and dashboard evidence, and provides a consolidated works cited section.
- [Eight-slide presentation](output/presentation/AI_Economic_Perceptions_Consumer_Sentiment_Presentation_v16.pptx). The deck presents one practical implication for financial forecasting: treat a sentiment gap as a model-risk signal that starts a documented review rather than an automatic forecast adjustment.
- [Presentation speaker script](output/presentation/Presentation_Speaker_Script.md), designed for a six- to eight-minute delivery.

The notebook at [notebooks/perceptual_bias_analysis.ipynb](notebooks/perceptual_bias_analysis.ipynb) remains the reproducible source for the supplementary analysis. The dashboard, report, and presentation distinguish forecasting evidence from causal claims throughout.

## Quick start

Use a Python environment with the packages in `requirements.txt`.

```bash
python scripts/refresh_public_macro.py
python scripts/build_control_vintage_archive.py
python scripts/build_realtime_macro_panel.py
python scripts/validate_media_labels.py
python scripts/build_media_model_analysis.py
python scripts/build_source_comparative_benchmark.py
python scripts/build_causal_association_analysis.py
python src/pipeline.py
python scripts/collect_media_corpus.py
python scripts/build_annotation_packets.py
jupyter lab notebooks/perceptual_bias_analysis.ipynb
python -m http.server 8000 --directory dashboard
```

Open `http://localhost:8000` for the dashboard. Re-run the pipeline after replacing `data/raw/Perceptual_Bias_Data.xlsx`, refreshing public controls, or adding a validated `data/media_monthly.csv`.

## What is implemented

- Chronology-respecting economic-only rolling forecasts of Michigan consumer sentiment, with 95% prediction intervals and a sentiment gap.
- A supplementary household-stress proxy extension using 12-month unemployment change and a GDP-based recession signal. It tests incremental prediction, not a causal effect.
- A static dashboard for the sentiment prediction, gap, macro series, model metrics, data quality, model ladder, current-vintage refresh status, and media-measure status.
- A documented public-macro refresh covering PCE price level/cumulative change, real disposable income, U-6, debt service, housing affordability, and policy uncertainty. Each snapshot has a retrieval manifest and hash.
- A 2010-present ALFRED initial-release panel and a month-end vintage macro forecast comparator, plus an autocorrelation-aware lagged-sentiment sensitivity model.
- A full ALFRED vintage archive for U-6, real disposable income, PCE prices, household debt service, and the legacy three-component monthly EPU index, with raw-response hashes and dated information snapshots. Housing affordability remains explicitly blocked pending a primary-source vintage archive.
- A media-input contract, completed 312-item source-blinded all-field validation/adjudication workflow, conventional development-only classifier workflow, AI-measurement protocol, and human-labeling guide. Machine labels are excluded from agreement statistics by design.
- A gated historical media-model builder with a pre-specified one-month media lag, seasonal terms, chronological holdouts, lag sensitivity, residual diagnostics, coefficient-stability summaries, and a common-sample economic-plus-media-plus-household-controls specification using archived ALFRED snapshots.
- A source-comparative content-supply benchmark that pairs retained items within publication-day and pre-specified topic cells; it reports contrasts without calling them exposure, ideological bias, or causal effects.
- A balanced, documented 315-item coding sample drawn from a 539-record headline/news-card and public-social corpus. See [corpus documentation](data/corpus/README.md).
- A retrospective, explicitly non-causal association analysis with a future-media placebo, a pre-registration-ready factual-framing protocol, and documented Michigan survey-method comparability.
- A completed written report and an eight-slide presentation that synthesize the notebook, dashboard, forecast comparisons, measurement validation, and causal-design limits for a financial-forecasting audience.

## Important limitations

The source workbook contains only the headline Michigan index, U-3, PCE YoY, and quarterly GDP growth. The project adds ALFRED initial-release macro values and final Michigan subindex values. For 2010-2025, the values remain transcribed from annual December final-result reports, while their availability dates now use the University of Michigan's original monthly final-release schedule (date only). Public age-group ICS values are loaded as three-month moving averages; their displayed `Cases` values are source metadata, not asserted pooled analytic bases. Verified subgroup ICC/ICE component coverage is frozen at February 2026 pending confirmation of the archive production rule; the March–August 2026 archive query returned no records on 2026-10-14. The historical archive has 89 aligned months, so its tone-only chronological comparison is enabled. The results are retrospective and associational, not causal estimates or evidence that coverage is biased.

See [data provenance](data/README.md), [external-data notes](data/external/README.md), [coding guide](docs/human_labeling_guide.md), [AI validation protocol](docs/ai_measurement_validation.md), [causal design](docs/causal_design_protocol.md), and [dashboard notes](dashboard/README.md) before interpreting or extending the project.
