"""Add linked, auditable citations to the Markdown report after DOCX conversion."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "output/report/AI_Economic_Perceptions_Consumer_Sentiment_Report.md"
text = path.read_text()

replacements = {
    "The project treats a negative residual as unexplained pessimism under a specified model, not as proof that consumers are irrational or that coverage is biased.":
        "The project treats a negative residual as unexplained pessimism under a specified model, not as proof that consumers are irrational or that coverage is biased.[^brief][^project-readme]",
    "- A chronology-respecting economic-only rolling forecast has an out-of-sample MAE of 12.579 index points and RMSE of 16.458 across 126 forecasts. Its residuals are strongly autocorrelated, so it is a baseline rather than a complete explanation.":
        "- A chronology-respecting economic-only rolling forecast has an out-of-sample MAE of 12.579 index points and RMSE of 16.458 across 126 forecasts. Its residuals are strongly autocorrelated, so it is a baseline rather than a complete explanation.[^run-summary]",
    "- The project adds a household-stress proxy and a broader control set. The expanded-controls forecast reduces MAE to 4.467 and RMSE to 6.236 across 142 out-of-sample forecasts, demonstrating that headline macro indicators are not the whole household experience.":
        "- The project adds a household-stress proxy and a broader control set. The expanded-controls forecast reduces MAE to 4.467 and RMSE to 6.236 across 142 out-of-sample forecasts, demonstrating that headline macro indicators are not the whole household experience.[^run-summary]",
    "- Two source-blinded human coders independently labeled 312 retained items. Tone agreement was 59.3% with Cohen kappa of 0.437; disagreements were adjudicated before a monthly media measure was constructed.":
        "- Two source-blinded human coders independently labeled 312 retained items. Tone agreement was 59.3% with Cohen kappa of 0.437; disagreements were adjudicated before a monthly media measure was constructed.[^validation][^dashboard-payload]",
    "- In the 2014-2021 historical archive, a 10 percentage-point increase in prior-month negative tone is associated with an 8.09-point lower headline sentiment reading after controls. This is an observational association, not a causal media effect.":
        "- In the 2014-2021 historical archive, a 10 percentage-point increase in prior-month negative tone is associated with an 8.09-point lower headline sentiment reading after controls. This is an observational association, not a causal media effect.[^causal-results][^causal-protocol]",
    "- Adding historical media tone does not improve MAE in the primary historical rolling forecast (6.04 versus 5.93 for economic-only), even though RMSE declines modestly (9.84 versus 10.63). The practical conclusion is to monitor narratives as risk signals, not to insert them mechanically into a production forecast.":
        "- Adding historical media tone does not improve MAE in the primary historical rolling forecast (6.04 versus 5.93 for economic-only), even though RMSE declines modestly (9.84 versus 10.63). The practical conclusion is to monitor narratives as risk signals, not to insert them mechanically into a production forecast.[^media-model]",
    "The design therefore separates prediction from explanation and association from causal impact.":
        "The design therefore separates prediction from explanation and association from causal impact.[^brief][^causal-protocol]",
    "The reproducible package supplements it with documented public macro series and an ALFRED-vintage archive.":
        "The reproducible package supplements it with documented public macro series and an ALFRED-vintage archive.[^michigan][^bls][^bea][^alfred]",
    "Table 2. Latest stored baseline comparison. October is explicitly treated as a partial-period observation. Source: project output economic_only_oos.csv.":
        "Table 2. Latest stored baseline comparison. October is explicitly treated as a partial-period observation. Source: project output economic_only_oos.csv.[^run-summary][^dashboard-payload]",
    "It does not scrape paywalled article bodies, comments, advertisements, or profiles.":
        "It does not scrape paywalled article bodies, comments, advertisements, or profiles.[^corpus]",
    "The evidence is too imprecise to support a broad comparative claim.":
        "The evidence is too imprecise to support a broad comparative claim.[^media-monthly][^dashboard-payload]",
    "The completed all-field workflow covers 312 finalized items.":
        "The completed all-field workflow covers 312 finalized items.[^validation][^dashboard-payload]",
    "Table 4. Adjudicated 2026 media-tone mix. Availability reflects final-label build timing, not publication-date exposure. Source: project media_monthly.csv.":
        "Table 4. Adjudicated 2026 media-tone mix. Availability reflects final-label build timing, not publication-date exposure. Source: project media_monthly.csv.[^media-monthly]",
    "Performance should be read alongside residual diagnostics, because a low error can still conceal serial dependence or timing leakage.":
        "Performance should be read alongside residual diagnostics, because a low error can still conceal serial dependence or timing leakage.[^run-summary][^notebook]",
    "The timing-and-model-limit hypothesis is also supported by the baseline residual autocorrelation, release-vintage sensitivity, survey-method caveats, and the partial-period cutoff.":
        "The timing-and-model-limit hypothesis is also supported by the baseline residual autocorrelation, release-vintage sensitivity, survey-method caveats, and the partial-period cutoff.[^run-summary][^media-model][^michigan-transition]",
    "The archive contains 89 aligned months from January 2014 through June 2021.":
        "The archive contains 89 aligned months from January 2014 through June 2021.[^causal-results][^causal-protocol]",
    "A nonzero future-media placebo would count against a simple directional account; a null placebo does not demonstrate causality.":
        "A nonzero future-media placebo would count against a simple directional account; a null placebo does not demonstrate causality.[^causal-results][^causal-protocol]",
    "Empty media values remain missing rather than being converted to zeros.":
        "Empty media values remain missing rather than being converted to zeros.[^dashboard-payload]",
    "Survey methodology changes also limit naïve comparisons across periods.":
        "Survey methodology changes also limit naïve comparisons across periods.[^michigan-transition]",
    "The notebook is a reproducible narrative around the pipeline. Its code cells construct the following tables and diagnostics; the notebook itself does not retain rendered plot outputs, so the report reproduces the results from the saved pipeline artifacts and dashboard payload.":
        "The notebook is a reproducible narrative around the pipeline. Its code cells construct the following tables and diagnostics; the notebook itself does not retain rendered plot outputs, so the report reproduces the results from the saved pipeline artifacts and dashboard payload.[^notebook][^dashboard-payload]",
    "The model is retrospective and associational.":
        "The model is retrospective and associational.[^causal-results][^causal-protocol]",
    "- Michigan’s 2024 transition from telephone random-digit dialing to address-based web collection requires a documented comparability sensitivity before interpreting cross-transition changes.":
        "- Michigan’s 2024 transition from telephone random-digit dialing to address-based web collection requires a documented comparability sensitivity before interpreting cross-transition changes.[^michigan-transition]",
    "- The public macro refresh is current-vintage monitoring data; historical real-time testing requires archived release vintages.":
        "- The public macro refresh is current-vintage monitoring data; historical real-time testing requires archived release vintages.[^alfred]",
}

for old, new in replacements.items():
    if old not in text:
        raise RuntimeError(f"Expected text not found: {old[:80]}")
    text = text.replace(old, new, 1)

table_notes = {
    "| Causal evidence | Pre-specified randomized truthful-framing experiment proposed for future work. | A feasible next step, subject to approval and fielding. |\n":
        "| Causal evidence | Pre-specified randomized truthful-framing experiment proposed for future work. | A feasible next step, subject to approval and fielding. |\n\nSource: course brief and project causal-design protocol.[^brief][^causal-protocol]\n",
    "| Supplementary controls | U-6, real income, cumulative prices, debt service, housing affordability, policy uncertainty. | Controls improve description; they do not solve causal identification. |\n":
        "| Supplementary controls | U-6, real income, cumulative prices, debt service, housing affordability, policy uncertainty. | Controls improve description; they do not solve causal identification. |\n\nSources: Michigan, BLS, BEA, ALFRED, and EPU documentation; project data contract.[^michigan][^bls][^bea][^alfred][^epu][^project-readme]\n",
    "| Invariance checks | Actor-name/source masking protocol included | A no-change dictionary result is not a validation claim for an LLM. |\n":
        "| Invariance checks | Actor-name/source masking protocol included | A no-change dictionary result is not a validation claim for an LLM. |\n\nSource: project validation protocol and dashboard payload.[^validation][^dashboard-payload]\n",
    "| Expanded macro controls | 142 | 4.467 | 6.236 | 83.1% | 0.586 |\n":
        "| Expanded macro controls | 142 | 4.467 | 6.236 | 83.1% | 0.586 |\n\nSource: reproducible run summary.[^run-summary]\n",
    "| Economic + media + archived controls | 41 | 7.920 | 18.612 | Worse out-of-sample performance; richer controls can increase estimation risk in a short sample. |\n":
        "| Economic + media + archived controls | 41 | 7.920 | 18.612 | Worse out-of-sample performance; richer controls can increase estimation risk in a short sample. |\n\nSource: historical media-model status artifact.[^media-model]\n",
    "| Expectations | -7.31 | [-8.83, -5.79] | 0.529 |\n":
        "| Expectations | -7.31 | [-8.83, -5.79] | 0.529 |\n\nSource: causal association results.[^causal-results]\n",
    "| Communication risk | Describe media measures as content supply and report missingness. | Avoids implying exposure, persuasion, or ideology that the data cannot observe. |\n":
        "| Communication risk | Describe media measures as content supply and report missingness. | Avoids implying exposure, persuasion, or ideology that the data cannot observe. |\n\nSource: dashboard monitoring payload and corpus documentation.[^dashboard-payload][^corpus]\n",
    "| Validated media panels | Monthly tone, factual calibration, salience, framing, source composition, item count, and missingness. | Final-label availability time is not a real-time publication timestamp. |\n":
        "| Validated media panels | Monthly tone, factual calibration, salience, framing, source composition, item count, and missingness. | Final-label availability time is not a real-time publication timestamp. |\n\nSource: dashboard monitoring payload.[^dashboard-payload]\n",
    "| Release chronology and caveats | Verified final survey releases, monitoring cutoff, method-comparability warning, and availability limitations. |\n":
        "| Release chronology and caveats | Verified final survey releases, monitoring cutoff, method-comparability warning, and availability limitations. |\n\nSource: dashboard monitoring payload and Michigan technical documentation.[^dashboard-payload][^michigan]\n",
    "| Dashboard build | Normalized panel, out-of-sample outputs, metadata, and current payload. | Dashboard evidence tables in this report. |\n":
        "| Dashboard build | Normalized panel, out-of-sample outputs, metadata, and current payload. | Dashboard evidence tables in this report. |\n\nSource: reproducible notebook and dashboard payload.[^notebook][^dashboard-payload]\n",
    "| Economic + media + archived controls | 41 | 7.920 | 18.612 | 68.3% |\n":
        "| Economic + media + archived controls | 41 | 7.920 | 18.612 | 68.3% |\n\nSources: run summary and historical media-model status artifact.[^run-summary][^media-model]\n",
    "| Oct 2026 | 215 | 17 | 35.8% | 14.9% | 7.4% | 85.1% | 14.9% | 18.6% |\n":
        "| Oct 2026 | 215 | 17 | 35.8% | 14.9% | 7.4% | 85.1% | 14.9% | 18.6% |\n\nSource: adjudicated monthly media measures.[^media-monthly]\n",
    "| Political attribution: national minus local | 18 | +11.11 pp | [-9.17, 31.40] | Imprecise; not ideological-bias evidence. |\n":
        "| Political attribution: national minus local | 18 | +11.11 pp | [-9.17, 31.40] | Imprecise; not ideological-bias evidence. |\n\nSource: dashboard monitoring payload.[^dashboard-payload]\n",
    "| Full-field classifier | 252 development and 60 released holdout rows; no further tuning permitted. | Held-out diagnostic only; preserve model hash and run baseline. |\n":
        "| Full-field classifier | 252 development and 60 released holdout rows; no further tuning permitted. | Held-out diagnostic only; preserve model hash and run baseline. |\n\nSource: dashboard monitoring payload and validation protocol.[^dashboard-payload][^validation]\n",
    "| Expectations | 89 | -7.312 | 0.775 | [-8.831, -5.794] | 0.730 | 0.529 |\n":
        "| Expectations | 89 | -7.312 | 0.775 | [-8.831, -5.794] | 0.730 | 0.529 |\n\nSource: causal association results.[^causal-results]\n",
    "| Monitoring update plan | Refresh after each verified Michigan final release and major-event entry through election day. | Archive inputs, vintages, labels, and outputs for every run. |\n":
        "| Monitoring update plan | Refresh after each verified Michigan final release and major-event entry through election day. | Archive inputs, vintages, labels, and outputs for every run. |\n\nSource: dashboard monitoring payload and Michigan survey documentation.[^dashboard-payload][^michigan]\n",
}

for old, new in table_notes.items():
    if old not in text:
        raise RuntimeError(f"Expected table end not found: {old[:80]}")
    text = text.replace(old, new, 1)

source_heading = "## References and reproducible materials"
if source_heading not in text:
    source_heading = "## Sources and citation notes"
start = text.index(source_heading)
end = text.index("## Dashboard inventory and current monitoring state")
sources = '''## Works cited

Project artifacts are listed alongside external data and methodology sources so that every reported estimate remains auditable and reproducible.

1. Baker, Scott R., Nicholas Bloom, and Steven J. Davis. “[Economic Policy Uncertainty: Methodology](https://www.policyuncertainty.com/methodology.html).” Accessed October 14, 2026.
2. Federal Reserve Bank of St. Louis. “[ALFRED: Archival Federal Reserve Economic Data](https://alfred.stlouisfed.org/).” Accessed October 14, 2026. See also “[Download Data Help](https://alfred.stlouisfed.org/help/downloaddata).”
3. University of Michigan, Surveys of Consumers. “[Survey Description](https://data.sca.isr.umich.edu/survey-description.php)” and “[Technical Documentation](https://data.sca.isr.umich.edu/technical-docs.php).” Accessed October 14, 2026.
4. University of Michigan, Surveys of Consumers. “[Methodology Transition Announcement, 2024](https://www.sca.isr.umich.edu/files/methodtransitionannouncement2024.pdf).”
5. U.S. Bureau of Economic Analysis. “[BEA Data](https://www.bea.gov/v2/data)” and “[Consumer Spending / PCE](https://www.bea.gov/data/consumer-spending/main).” Accessed October 14, 2026.
6. U.S. Bureau of Labor Statistics. “[Labor Force Statistics from the Current Population Survey](https://www.bls.gov/cps/cps_over.htm).” Accessed October 14, 2026.
7. *AI Applications in Finance*. “[Final Project: Applications in Finance, October 2026](/Users/alanwang/Downloads/Final_Project_Applications_in_Finance_Oct_2026.pdf).” Course brief.
8. Project repository. “[README](../../README.md).” Research scope, implementation overview, and interpretation boundaries.
9. Project repository. “[Corpus documentation](../../data/corpus/README.md).” Collection, retention, and content-supply boundaries.
10. Project repository. “[AI measurement validation protocol](../../docs/ai_measurement_validation.md).” Independent-label and adjudication procedure.
11. Project repository. “[Causal-design protocol](../../docs/causal_design_protocol.md).” Association design, non-identification statement, and proposed experiment.
12. Project repository. “[Reproducible analysis notebook](../../notebooks/perceptual_bias_analysis.ipynb).” Analysis workflow and diagnostic generation.
13. Project repository. “[Run summary](../../data/processed/run_summary.json).” Out-of-sample forecast metrics and model comparison.
14. Project repository. “[Historical media-model status](../../data/processed/media_model_status.json).” Historical forecast comparison and archive coverage.
15. Project repository. “[Causal association results](../../data/processed/causal_association_results.csv).” HAC estimates and future-media placebo.
16. Project repository. “[Adjudicated monthly media measures](../../data/media_monthly.csv).” Monthly tone, framing, calibration, and source composition.
17. Project repository. “[Dashboard monitoring payload](../../dashboard/data/monitoring_payload.json).” Current monitoring values, displays, and readiness metadata.

'''
text = text[:start] + sources + text[end:]

citation_numbers = {
    "epu": 1, "alfred": 2, "michigan": 3, "michigan-transition": 4,
    "bea": 5, "bls": 6, "brief": 7, "project-readme": 8, "corpus": 9,
    "validation": 10, "causal-protocol": 11, "notebook": 12,
    "run-summary": 13, "media-model": 14, "causal-results": 15,
    "media-monthly": 16, "dashboard-payload": 17,
}
for key, number in citation_numbers.items():
    text = text.replace(f"[^{key}]", f"[{number}]")
path.write_text(text)
print(path)
