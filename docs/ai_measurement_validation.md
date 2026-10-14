# AI-assisted media measurement and validation protocol

The existing dictionary labels are triage aids, not human annotations, ground truth, or an independent second rater. Do not estimate a media effect until this protocol produces eligible human-label agreement and an adjudicated monthly measure.

## Required item-level evidence

Each retained item needs its corpus ID, stable URL, publisher/platform, publication timestamp and timezone, query/source stratum, exact available headline/excerpt (or licensed full text), collection timestamp, retrieval status, and source snapshot/hash. Preserve an access/licensing decision rather than silently replacing inaccessible text.

## Human and model workflow

1. Blind two independent annotators to outlet identity, political cues where feasible, and each other's decisions.
2. Record tone (`negative`, `neutral`, `positive`, `mixed`, `unclear`), framing flags, salience, factual-calibration assessment, evidence span, and confidence. Use the supplied coding guide.
3. Run `python scripts/validate_media_labels.py`. The gate requires at least 300 paired independent human tone labels and reports raw agreement, Cohen's kappa, and disagreements. Machine-assisted rows are excluded.
4. Adjudicate disagreements into an immutable `adjudicated_labels.csv`, preserving both original votes and adjudicator/reason.
5. Compare the versioned classifier against adjudication by tone and framing: accuracy, macro-F1, per-class precision/recall, confusion matrix, calibration if probabilistic, and error slices by source type/time/topic.

## Model-card fields

For every machine run preserve model/provider/version, prompt template and hash, system instructions, decoding settings, date, code/data commit, input policy, output schema, failures, human reviewer, and evaluation set. Use evidence spans; never ask a model to infer facts absent from the retrieved text.

## Invariance and robustness tests

Before use, reclassify a held-out sample after (a) masking outlet/platform names, (b) swapping political actor names with neutral placeholders, (c) removing engagement counts, and (d) truncating to the retained evidence span. Report changed-label rates and inspect all changes. Run source-stratified and time-stratified error analyses. A no-change result for a dictionary is not validation of an LLM or of construct validity.

## Monthly construction

Use publication time converted to a declared timezone, apply predeclared source/platform weights, retain item counts/effective sample size, and publish uncertainty (bootstrap or design-aware interval). Missing months are missing, not zero. Align a month only after all inputs were publicly available; store the availability timestamp used.
