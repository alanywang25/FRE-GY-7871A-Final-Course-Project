# Human-labeling guide

## Unit and sampling

Label one immutable item at a time: a news headline, article, post, or comment. Record its source, source family, URL or archive ID, publication timestamp, observed/available timestamp, geography, text type, audience field if available, duplicate/repost/advertising status, and suspected automation flag. Do not merge headlines with body text.

Draw a stratified validation sample of at least 300 retained items across month, source family, text type, and preliminary tone. Two independent annotators label every sampled item while blinded to source name where feasible. Preserve initial labels, then adjudicate disagreements with a written rationale. Report per-class agreement (Cohen's kappa or Krippendorff's alpha), source-specific error, confusion matrices, and the excluded-item rate.

## Codebook

| Field | Allowed labels | Decision rule |
| --- | --- | --- |
| Tone | negative / neutral / positive / mixed | Code the economic language, not whether the economic fact is good or bad. Mark `mixed` when meaningful positive and negative claims coexist. |
| Salience | layoffs / hiring / price-level / disinflation / growth / recession-risk / other | Multi-label. Code the concrete economic topic receiving attention. |
| Frame | price-level / inflation-rate / household-experience / national-aggregate / current / forecast | Multi-label. Frame is the angle, not the factual direction. |
| Factual calibration | calibrated / materially incomplete-or-misleading / unverifiable | Check numerical claims against information actually available at publication. Record the benchmark and a short evidence excerpt. |
| Political attribution | none / named actor or institution | Record the exact target and whether blame, credit, or neutral association is stated. Criticism is not bias by itself. |

## Benchmarking and model validation

Compare coverage of the same official release, comparable positive and negative surprises, and identical event windows across sources. Retain the prompt, model/provider/version, temperature, retrieval material, output, and evidence excerpt. Compare the AI labels against a dictionary or conventional classifier. Run counterfactual text tests that swap political names and source labels while holding the remaining text fixed. Report changes as classifier sensitivity, not as evidence about people.

## Guardrails

Content can establish framing or selective coverage, but it cannot establish confirmation or availability bias among readers. Do not use likes or reposts as exposure. Keep supply, engagement, and exposure distinct. Do not run a media-augmented time-series model until the observation availability time and missing-data process are documented.
