# Causal-design extension: factual economic framing experiment

This is a preregistration-ready design proposal, not an executed experiment and not evidence of a media causal effect.

## Implemented observational supplement

`scripts/build_causal_association_analysis.py` is the project's reproducible
observational complement. It joins the independently validated historical
negative-tone aggregate to headline Michigan sentiment and the Current Economic
Conditions and Expectations subindices. The primary descriptive specification
uses prior-calendar-month negative tone, a lagged outcome, unemployment, PCE
inflation, quarterly real-GDP growth, calendar seasonality, and HAC(6)
uncertainty. It also estimates a future-media placebo. The results are written
to `data/processed/causal_association_results.csv` and surfaced as
**associational, not causal** in the dashboard.

The historical subindices in 2010-2025 are final values transcribed from annual
December reports. They can be used as retrospective outcomes here, but their
annual backfill timestamp must not be treated as the original month-by-month
release availability. A null placebo does not establish causality; a non-null
placebo is evidence against a simple directional media interpretation.

The observational estimates do not identify an effect because economic shocks,
political events, publisher and audience demand, selective media consumption,
and other household conditions can affect both tone and sentiment. There is no
respondent-level exposure measure, no treatment assignment, and no defensible
instrument in the supplied data.

## Question and estimand

Among eligible adult respondents, what is the average effect of a balanced, source-blinded factual economic framing versus a neutral factual control on near-term and one-year consumer-expectation outcomes? The primary estimand is the intention-to-treat difference in post-treatment expectations, adjusted for its pre-treatment value.

## Treatments and outcomes

Randomly assign respondents with equal probability to: (1) a factual level-and-change framing showing inflation, real income, unemployment, and a clear source/date; (2) an uncertainty framing using the same verified figures and explicit uncertainty; or (3) a neutral, non-economic factual control. Counterbalance card order and headline formatting. Do not use deceptive claims or alter quotes.

Measure pre/post one-year outlook, expected inflation, perceived purchasing power, confidence in the information, comprehension, and item recall. Predeclare one primary outcome and label the rest secondary. Collect consent, age eligibility, attention/comprehension checks, and minimal covariates needed for balance/heterogeneity.

## Analysis plan

Estimate OLS/GLM intention-to-treat models with treatment indicators and pre-treatment outcome; report unadjusted estimates, robust standard errors, 95% intervals, standardized effects, and all assignment arms. Lock randomization before fielding. Report attrition by arm, balance diagnostics, treatment uptake, exclusions, missing-data handling, multiplicity adjustment for secondary outcomes, and sensitivity to attention-check rules. Analyze treatment-effect heterogeneity only for predeclared subgroups with interaction terms and uncertainty intervals.

## Threats and safeguards

Use concealed allocation, one response per participant, randomized display order, source-blind stimuli, and a post-fielding manipulation check. Flag spillovers/duplicate participation, differential attrition, demand effects, temporal shocks, and limits to generalizing from the recruited sample. Obtain required instructor/IRB approval before recruiting or collecting identifiable data. Archive stimulus text, sources, version hashes, consent language, preregistration, anonymized code, and a data dictionary.

## Bridge to the national Michigan index

Even a successfully randomized study estimates an effect in the recruited sample,
not an effect on the national Michigan index. Making that bridge would require a
representative sampling frame or defensible survey weights, documented exposure
rates by treatment-relevant subgroup, measurement equivalence with Michigan
outcomes, transportability assumptions, and an aggregation model. The project
does not make that bridge.
