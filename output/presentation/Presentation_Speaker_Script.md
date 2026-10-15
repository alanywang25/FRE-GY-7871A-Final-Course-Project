# Presentation Speaker Script

Target length: 6 to 8 minutes

## Slide 1 - When consumer sentiment diverges from macro data

Consumer sentiment can move sharply away from what headline macroeconomic indicators would suggest. The practical question is not whether that gap proves consumers are wrong or that media coverage is biased. It is whether the gap should change a forecast, or first change an analyst's uncertainty assessment. This project recommends the second response: treat the gap as a model-risk signal that starts a governed review before any forecast or risk action.

## Slide 2 - A sentiment gap starts a review

Three explanations can coexist. First, headline growth and inflation may miss household pressures such as broader unemployment, debt service, housing affordability, or the accumulated price level. Second, narratives and framing may shape the information environment, although the text data in this project measure content supply rather than exposure or belief. Third, a gap can reflect timing, data revisions, survey-method changes, autocorrelation, or a short estimation sample. A negative residual therefore identifies uncertainty. It does not, by itself, tell us which explanation is correct.

## Slide 3 - The baseline uses information available on the decision date

The baseline combines the Michigan consumer sentiment index with U-3 unemployment, PCE inflation, and quarterly GDP growth. It uses documented availability rules and does not convert quarterly GDP into invented monthly values. The broader-control analysis adds U-6, income, cumulative prices, debt service, housing affordability, and policy uncertainty to test whether headline indicators omit relevant household conditions. The media corpus has a different role. It records tone, framing, salience, and factual calibration in sampled content, but it cannot establish engagement or respondent exposure.

## Slide 4 - Validated narrative measures can support review

The narrative measures pass a basic quality gate before entering the review process. Two independent, source-blinded reviewers labeled 312 items. Their raw agreement was 59.3 percent and Cohen's kappa was 0.437, which is moderate rather than definitive agreement. Original votes, final decisions, evidence excerpts, source metadata, and model records are retained. The key boundary matters: a dictionary does not validate a large language model, and a content label does not show who saw, remembered, or believed the content.

## Slide 5 - Broader household measures improve the forecast; media does not

The economic-only model has an out-of-sample MAE of 12.579. A household-stress proxy reduces MAE to 8.178, and the expanded public-control model reduces it to 4.467. Those gains indicate that the narrow baseline misses relevant household information. They do not identify a causal share of the sentiment gap. In the historical common-sample comparison, adding one-month lagged media tone does not improve MAE, and the version with media plus archived controls performs worse. The evidence therefore favors broader household measures over media tone as a forecasting extension.

## Slide 6 - Media helps prioritize research, not change a forecast

The historical association analysis finds that higher prior-month negative tone is associated with lower headline sentiment, Current Conditions, and Expectations. The models use lagged outcomes, U-3, PCE, GDP, seasonality, and Newey-West uncertainty, and they include a future-media placebo. Even so, 89 aligned months cannot solve the identification problem. Economic shocks, selective consumption, publisher incentives, and unobserved household conditions can affect both content tone and sentiment. Without respondent-level exposure or an external treatment, these estimates are useful for research triage, not a causal forecast input.

## Slide 7 - A governed narrative-risk forecast overlay

An analyst can use the availability-aware baseline, measurement documentation, disclosed missingness, source-content comparisons, and historical associations as context in a review. The analyst should not infer that negative coverage is biased, that respondents saw the sampled content, or that media tone caused national sentiment. The decision rule is simple: start a review, keep uncertainty visible, and seek corroborating evidence. Changing a forecast because of media would require exposure evidence or a credible causal research design.

## Slide 8 - Release-day model-risk workflow

On each relevant release day, the dashboard supports four steps. Detect the gap and confirm the partial-period and release status. Diagnose it by comparing forecast variants, vintages, revisions, household controls, and survey comparability. Review the validated narrative measures only as context. Then archive the inputs, labels, vintages, performance results, event log, and missing-data status. The practical implication is conservative: the organization may widen uncertainty or retain the forecast while the evidence remains incomplete, but it should not make automatic narrative-driven forecast changes.

## Slide 9 - References

The written report contains the complete works cited list and links to the project artifacts. The core external sources are the University of Michigan Surveys of Consumers, ALFRED, the Bureau of Labor Statistics, the Bureau of Economic Analysis, and the Economic Policy Uncertainty index documentation. The project repository supplies the reproducible notebook, validation records, dashboard payload, and causal-design protocol.
