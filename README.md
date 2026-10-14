# AI, Economic Perceptions, and Consumer Sentiment

This project implements the technical deliverables for the final project (the research report and summary presentation are intentionally excluded): a reproducible analysis, data/corpus/annotation infrastructure, a validation and causal-design package, and an updateable monitoring dashboard. It does **not** claim that media bias explains sentiment: forecast improvement is associational, and the project has no respondent-level exposure evidence.

## Quick start

Use a Python environment with the packages in `requirements.txt`.

```bash
python scripts/refresh_public_macro.py
python scripts/validate_media_labels.py
python scripts/build_media_model_analysis.py
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
- A media-input contract, completed independent tone-label validation/adjudication workflow, AI-measurement protocol, and human-labeling guide. Machine labels are excluded from agreement statistics by design.
- A gated historical media-model builder with a pre-specified one-month media lag, seasonal terms, chronological holdouts, lag sensitivity, residual diagnostics, and coefficient-stability summaries. It refuses to estimate when aligned history is inadequate.
- A balanced, documented 315-item coding sample drawn from a 539-record headline/news-card and public-social corpus. See [corpus documentation](data/corpus/README.md).
- A pre-registration-ready factual-framing causal-design protocol, plus release/event and subgroup data templates.

## Important limitations

The source workbook contains only the headline Michigan index, U-3, PCE YoY, and quarterly GDP growth. The public refresh is current-vintage data, not a historical release-vintage reconstruction. Populate `data/templates/michigan_subindices.csv`, `data/templates/macro_vintage_observations.csv`, `data/templates/michigan_subgroups.csv`, and `data/templates/release_event_log.csv` with authoritative records to complete those inputs. The historical media archive currently has 60 aligned months; the media-model builder requires 84 before estimating. The results are retrospective and the timing rules are documented approximations. They are not causal estimates and should not be used to characterize coverage as biased.

See [data provenance](data/README.md), [external-data notes](data/external/README.md), [coding guide](docs/human_labeling_guide.md), [AI validation protocol](docs/ai_measurement_validation.md), [causal design](docs/causal_design_protocol.md), and [dashboard notes](dashboard/README.md) before interpreting or extending the project.
