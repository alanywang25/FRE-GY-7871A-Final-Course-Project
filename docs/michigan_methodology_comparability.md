# Michigan survey-method comparability

## Documented transition

The University of Michigan's technical documentation records a 2024 transition
from random-digit-dialing cellular telephone interviews to address-based-sample
web surveys: telephone collection in January-March, a mixed mode in April-June,
and web collection from July onward. The publisher provides a technical report,
web/phone time-series comparisons, codebooks, and historical release dates.

Primary sources:

- [Technical documentation](https://data.sca.isr.umich.edu/technical-docs.php)
- [Methodological Transition to Web Surveys (2024)](https://data.sca.isr.umich.edu/fetchdoc.php?docid=75437)
- [2026 release calendar](https://data.sca.isr.umich.edu/fetchdoc.php?docid=79628)

## Implementation rule

All dashboard and notebook interpretations flag the transition. The historical
media and causal-association panels end in June 2021, so they do not cross it.
The long macro forecast does cross it, but only a small post-transition
out-of-sample segment is currently available; the repository therefore reports
the transition as a comparability limitation rather than estimating a
transition effect or re-scaling the index.

## Required before a comparability claim

Use the publisher's mode-comparison material to pre-specify a break test or
mode-adjustment sensitivity; report pre/mixed/post estimates separately with
their uncertainty; and retain the exact release vintage. Do not attribute a
post-2024 change in sentiment to media, election proximity, or the collection
mode without this evidence.
