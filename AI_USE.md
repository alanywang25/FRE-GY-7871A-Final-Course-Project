# AI use disclosure

**Tools used:** Codex

**What I used them for:** I used Codex to build and revise the reproducible Python pipeline, Jupyter notebook, and local monitoring dashboard, as well as create data contracts, annotation packets, validation/adjudication utilities, and documentation. In addition, I used Codex to help process provided Michigan, FRED/ALFRED, EPU, and NAR inputs,  construct availability-dated macro and media panels, and run reproducibility and syntax checks. I also used to help draft the observational causal-design protocol. 

**What I wrote myself:** I supplied the retrieved and provided source documents and data whenever it had to be manually done, configured local API credentials, manually reviewed and completed the annotator files and adjudication decisions whenever necessary, selected resolutions for labeling disagreements, and reviewed/corrected dashboard and analysis assumptions. I also wrote out the final report and presentation slide deck.

**Anything the model got wrong that I had to correct:** The initial implementation had  automated labeling and factual-calibration outputs that required manual review and correction. In addition, some early media-adjudication and independent-validation entries also needed to be replaced after manual review. The initial historical EPU approach used the daily `USEPUINDXD` series and a broken download workflow was corrected to the monthly legacy three-component `USEPUINDXM` series with point-in-time API requests. The initial implementation of the dashboard displayed October 2026 as a completed month and used an end-of-month date beyond the dated cutoff so it was instead corrected to a partial-period observation.
