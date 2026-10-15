"""Make the Markdown report guideline-complete and presentation-ready."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "output/report/AI_Economic_Perceptions_Consumer_Sentiment_Report.md"
text = PATH.read_text()

replacements = {
'''### Findings

- A chronology-respecting economic-only rolling forecast has an out-of-sample MAE of 12.579 index points and RMSE of 16.458 across 126 forecasts. Its residuals are strongly autocorrelated, so it is a baseline rather than a complete explanation.[13][13]
- The project adds a household-stress proxy and a broader control set. The expanded-controls forecast reduces MAE to 4.467 and RMSE to 6.236 across 142 out-of-sample forecasts, demonstrating that headline macro indicators are not the whole household experience.[13][13]
- Two source-blinded human coders independently labeled 312 retained items. Tone agreement was 59.3% with Cohen kappa of 0.437; disagreements were adjudicated before a monthly media measure was constructed.[10][17][10][17]
- In the 2014-2021 historical archive, a 10 percentage-point increase in prior-month negative tone is associated with an 8.09-point lower headline sentiment reading after controls. This is an observational association, not a causal media effect.[15][11][15][11]
- Adding historical media tone does not improve MAE in the primary historical rolling forecast (6.04 versus 5.93 for economic-only), even though RMSE declines modestly (9.84 versus 10.63). The practical conclusion is to monitor narratives as risk signals, not to insert them mechanically into a production forecast.[14][14]
''': '''### Findings

The chronology-respecting economic-only rolling forecast has an out-of-sample MAE of 12.579 index points and RMSE of 16.458 across 126 forecasts. Its residuals are strongly autocorrelated, so it is a baseline rather than a complete explanation. The expanded-controls forecast reduces MAE to 4.467 and RMSE to 6.236 across 142 out-of-sample forecasts, showing that headline macro indicators do not capture the full household-relevant information set.[13]

Two source-blinded human coders independently labeled 312 retained items. Tone agreement was 59.3% with Cohen kappa of 0.437, and disagreements were adjudicated before the monthly media measure was constructed.[10][17] In the 2014-2021 archive, a 10-percentage-point increase in prior-month negative tone is associated with an 8.09-point lower headline sentiment reading after controls, but this is an observational association rather than a causal media effect. Adding historical media tone does not improve the primary common-sample MAE (6.04 versus 5.93 for economic-only), even though RMSE declines modestly (9.84 versus 10.63); therefore, narratives are monitored as risk signals rather than inserted mechanically into a production forecast.[14][15][11]
''',
'''### Pre-registered interpretation rules

- Negative coverage is not defined as biased merely because it is negative. Bias would require a declared benchmark, such as comparable releases or matched topic-day content.
- Text data can measure content supply and framing but cannot establish what Michigan respondents encountered, recalled, or believed.
- A null or weak media forecast improvement would be evidence against a strong incremental-prediction claim; it would not prove that media never matters.
''': '''### Pre-specified interpretation rules

Negative coverage is not defined as biased merely because it is negative; a bias claim requires a declared benchmark, such as comparable releases or matched topic-day content. Text data measure content supply and framing, not what Michigan respondents encountered, recalled, or believed. Likewise, a null or weak media forecast improvement counts against a strong incremental-prediction claim, but does not prove that media never matters.[7][11]
''',
'''### Material limitations

- The original workbook has only the headline Michigan index, U-3, PCE YoY, and quarterly GDP growth. Subindices and added controls have different availability and revision characteristics.
- The historical media archive has 89 aligned months. Coefficients are unstable across specifications, and no respondent-level exposure or political-affiliation measure is available.
- The 2026 media aggregate is finalized after human coding. It is descriptive and should not be shown as a contemporaneously available predictor without rebuilding it under a prospective timestamp contract.
- Michigan subindices are final-report backfills for historical association, not evidence of real-time historical availability. Survey methodology changes also limit naïve comparisons across periods.[4][4]
- The corpus samples selected headlines/news cards and public social posts, not all articles or all household information environments.
''': '''### Material limitations

The original workbook contains the headline Michigan index, U-3, PCE year-over-year inflation, and quarterly GDP growth; subindices and expanded controls have different availability and revision characteristics. The historical media archive contains 89 aligned months, which makes coefficients specification-sensitive, and it contains neither respondent-level media exposure nor political affiliation. The 2026 media aggregate is finalized after human coding, so it is descriptive and cannot be treated as a contemporaneously available predictor without a prospective timestamp contract. Michigan subindices are final-report backfills for historical association rather than evidence of real-time historical availability, and the methodology transition further limits naive comparisons across periods.[4] Finally, the corpus samples selected headlines/news cards and public social posts, not the full household information environment.
''',
'''### Interpretive caveats retained in the dashboard

- Michigan’s 2024 transition from telephone random-digit dialing to address-based web collection requires a documented comparability sensitivity before interpreting cross-transition changes.[4][4]
- The public macro refresh is current-vintage monitoring data; historical real-time testing requires archived release vintages.[2][2]
- The dashboard does not assert verified subgroup ICC/ICE coverage after February 2026 because the March–August archive query returned no records.
- Any prospective analysis must keep the partial-month policy, date cutoff, release documentation, and missing-data flags visible.
''': '''### Interpretive caveats retained in the dashboard

Michigan’s 2024 transition from telephone random-digit dialing to address-based web collection requires a documented comparability sensitivity before interpreting cross-transition changes.[4] The public macro refresh is current-vintage monitoring data, whereas historical real-time testing requires archived release vintages.[2] The dashboard does not assert verified subgroup ICC/ICE coverage after February 2026 because the March-August archive query returned no records. Every prospective update must retain the partial-month policy, date cutoff, release documentation, and missing-data flags.
''',
'''### How the competing hypotheses fare
''': '''### Findings relative to the hypotheses
''',
}

for old, new in replacements.items():
    if old not in text:
        raise RuntimeError(f"Missing expected report block: {old[:60]!r}")
    text = text.replace(old, new, 1)

anchor = "Source: course brief and project causal-design protocol.[7][11]\n\n"
addition = '''## Hypotheses and planned tests

The household-pressure hypothesis states that the narrow macro baseline omits conditions that matter to households, including broader labor underutilization, real income, cumulative price levels, debt-service burdens, housing affordability, and policy uncertainty. It is supported only if a broader, availability-aware specification improves out-of-sample performance without relying on outcome leakage.

The information-and-framing hypothesis states that validated content-supply measures may be associated with sentiment or add incremental predictive value. The test is deliberately demanding: the coding must be auditable, the comparison must be against declared benchmarks, and media measures must improve chronological holdouts or remain stable in the historical association model. It does not presume that negative coverage is biased, or that content supply equals respondent exposure.

The timing-and-incomplete-model hypothesis states that the apparent gap can reflect release timing, data revisions, survey-method changes, partial periods, or omitted predictors. It is assessed through availability-aware vintages, residual autocorrelation, prediction intervals, model sensitivity, and explicit partial-period and methodological-transition flags.[2][4][11]

## Direct answers to the required research questions

### 1. How can bias in coverage or social media be measured?

Bias cannot be inferred from negativity alone. This project measures tone, selection and salience, framing, factual calibration, and political attribution, then assesses each against a declared content benchmark such as matched publication-day/topic cells or comparable economic releases. The available national-versus-local negative-tone contrast is +21.3 percentage points across 18 matched cells, but its interval spans -1.24 to +43.83 points. That result is too imprecise to establish systematic source bias.[9][16][17]

### 2. What impact is bias having on Michigan sentiment before the midterms?

The current evidence cannot determine a causal impact. Prior-month negative tone is associated with lower sentiment in the historical model, but the design lacks respondent-level exposure, exogenous variation, and a representative link from the content sample to Michigan respondents. Reverse causality, audience demand, and common economic or political shocks remain plausible. The appropriate next step is the documented randomized truthful-framing experiment or a credible exposure-based quasi-experiment, not a causal claim about the national index.[11][15]

### 3. How much of the discrepancy do unemployment, inflation, and GDP growth explain?

The economic-only model provides a useful but incomplete answer rather than a percentage decomposition. Its 126 chronological forecasts have MAE 12.579 and RMSE 16.458, and the partial October 2026 dashboard observation shows sentiment of 46.3 against a prediction of 75.3, a -29.0-point gap. Adding broader household-relevant controls improves forecasting performance, but the different specifications and samples do not identify a defensible share of the gap attributable to any one indicator.[13][17]

### 4. Which perceptual mechanisms can the data measure?

The data measure content-level negativity, issue salience, framing of price levels versus inflation rates, household versus national framing, factual calibration, and political attribution. They do not measure confirmation bias, availability bias, or price anchoring as respondent-level cognitive mechanisms because there are no exposure, recall, belief, or experimental outcomes. Cumulative prices are a household-pressure control, not evidence that respondents are cognitively anchored to past prices.[9][11][16]

### 5. Does media analysis improve predictions beyond economic indicators?

Not in the primary common historical holdout. Adding one-month negative media tone raises MAE from 5.929 to 6.040, while reducing RMSE from 10.629 to 9.836. The mixed result does not support a robust incremental-forecasting claim, particularly with only 41 common out-of-sample observations; media remains a monitored diagnostic rather than a production predictor.[14]

### 6. What evidence would contradict a media-bias explanation?

The project already contains several contradictory or limiting findings: weak incremental MAE performance, an imprecise matched-source contrast, a lack of observed exposure, and material improvement when broader household controls are added. A stable null result in future, pre-registered exposure-based tests, or a credible result showing that household pressures fully absorb the association, would further contradict a media-bias explanation. A null future-media placebo does not establish causality; it is only one timing diagnostic.[11][13][15][16]

'''
if anchor not in text:
    raise RuntimeError("Research-design source anchor not found")
text = text.replace(anchor, anchor + addition, 1)

figure_1 = '''![Figure 1. Dashboard sentiment and economic-only prediction](figures/figure_1_sentiment_forecast.svg)

Figure 1. Dashboard reproduction of the sentiment and economic-only prediction chart. The prediction interval and persistent deviations make clear why the gap is treated as a model diagnostic rather than a causal label.[17]

![Figure 2. Dashboard sentiment gap](figures/figure_2_sentiment_gap.svg)

Figure 2. Dashboard reproduction of observed sentiment minus the economic-only prediction. Negative values indicate unexplained pessimism under the specified economic model.[17]

'''
forecast_anchor = "The latest stored observation is partial-period October 2026 and should not be treated as a completed month. The dashboard visibly distinguishes data quality and availability from inferred conditions.\n\n"
if forecast_anchor not in text:
    raise RuntimeError("Forecast figure anchor not found")
text = text.replace(forecast_anchor, forecast_anchor + figure_1, 1)

figure_3 = '''![Figure 3. Dashboard validated media measures](figures/figure_3_validated_media_measures.svg)

Figure 3. Dashboard reproduction of the finalized, source-blinded media aggregate. The chart describes the retained content sample; it does not measure audience exposure or persuasion. October is partial-period.[16][17]

'''
media_anchor = "The measurement process preserves item IDs, exact retained text, source metadata, evidence spans, prompt/model records, adjudication records, and uncertainty. This makes future audit and recalibration possible while keeping the substantive claims limited to the measured construct.\n\n"
if media_anchor not in text:
    raise RuntimeError("Media figure anchor not found")
text = text.replace(media_anchor, media_anchor + figure_3, 1)

# Remove repeated adjacent citation sequences and duplicate adjacent source paragraphs.
previous = None
while previous != text:
    previous = text
    text = re.sub(r"(\[\d+\])\1+", r"\1", text)
    text = re.sub(r"((?:\[\d+\]){2,})(?:\1)+", r"\1", text)
    text = re.sub(r"(?m)^(Source(?:s)?:[^\n]+)\n\n\1\n", r"\1\n", text)

PATH.write_text(text)
print(PATH)
