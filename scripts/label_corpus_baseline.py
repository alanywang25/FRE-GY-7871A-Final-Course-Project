"""Create transparent provisional labels from the source-blinded coding packet.

These are a dictionary baseline for review. They are not human annotations, do
not establish factual calibration, and must not be counted as either required
independent annotator in the project brief.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "corpus" / "labeling" / "annotator_a.csv"
OUT = ROOT / "data" / "corpus" / "model_assisted"
OUTPUT = OUT / "dictionary_baseline_v1.csv"

RULES = {
    "negative": r"\b(inflation|unemployment|layoffs?|job cuts?|recession|downturn|contraction|declin(?:e|ed|ing)|slump|loss(?:es)?|risk|crisis|debt|foreclos(?:ure|ing)|unafford(?:able|ability)|surge|soar(?:ing)?|higher costs?)\b",
    "positive": r"\b(growth|grew|expansion|jobs? added|job gains?|hiring|rebound|recovery|cool(?:ing|ed)? inflation|eas(?:ing|ed) inflation|lower prices?|strong(?:er)? economy|record high|boost)\b",
    "salience_layoffs": r"\b(layoffs?|laid off|job cuts?|unemployment|unemployed)\b",
    "salience_hiring": r"\b(hiring|jobs? added|job gains?|payrolls?|employment|labor market)\b",
    "salience_price_level": r"\b(prices?|cost(?:s| of living)?|afford(?:able|ability)|rent|housing|grocer(?:y|ies)|wages?|paycheck)\b",
    "salience_disinflation": r"\b(disinflation|inflation (?:cooled|eased|slowed|fell|declined)|cool(?:ing|ed) inflation|eas(?:ing|ed) inflation)\b",
    "salience_growth": r"\b(gdp|growth|grew|expansion|economic output|economy (?:grew|expands?))\b",
    "salience_recession_risk": r"\b(recession|downturn|contraction|slump)\b",
    "frame_price_level": r"\b(prices?|cost(?:s| of living)?|afford(?:able|ability)|rent|housing|grocer(?:y|ies)|paycheck)\b",
    "frame_inflation_rate": r"\b(inflation|cpi|pce|consumer price index|percent|rate)\b",
    "frame_household_experience": r"\b(famil(?:y|ies)|households?|consumers?|workers?|paycheck|rent|grocer(?:y|ies)|afford(?:able|ability))\b",
    "frame_national_aggregate": r"\b(gdp|economy|economic output|nation(?:al|wide)?|u\.?s\.?|united states|federal reserve|fed)\b",
    "frame_current": r"\b(now|today|this month|latest|current|continues?|is|are|has|have)\b",
    "frame_forecast": r"\b(will|could|may|might|forecast|outlook|expect(?:s|ed)?|project(?:s|ed)?|next year|ahead)\b",
}
POLITICAL = r"\b(Trump|Biden|Congress|Republicans?|Democrats?|GOP|White House|Federal Reserve|Fed|Treasury|administration|government)\b"
COMPILED = {name: re.compile(pattern, re.I) for name, pattern in RULES.items()}


def hits(name: str, text: str) -> list[str]:
    return [match.group(0) for match in COMPILED[name].finditer(text)]


def clip_evidence(text: str, found: list[str]) -> str:
    if not found:
        return ""
    term = found[0]
    start = max(0, text.lower().find(term.lower()) - 45)
    end = min(len(text), start + 150)
    return text[start:end].strip()


def label(row: dict) -> dict:
    text = row["text"].strip()
    negative, positive = hits("negative", text), hits("positive", text)
    if negative and positive:
        tone = "mixed"
    elif negative:
        tone = "negative"
    elif positive:
        tone = "positive"
    else:
        tone = "neutral"
    values = {name: int(bool(hits(name, text))) for name in RULES if name not in {"negative", "positive"}}
    targets = [match.group(0) for match in re.finditer(POLITICAL, text, re.I)]
    target = "; ".join(dict.fromkeys(targets))
    lower = text.lower()
    if target and re.search(r"\b(blame|failed|failure|critic|fault|caused|hurt|worsen)\b", lower):
        valence = "blame"
    elif target and re.search(r"\b(credit|boost|helped|improved|success)\b", lower):
        valence = "credit"
    elif target:
        valence = "neutral"
    else:
        valence = ""
    triggers = negative + positive
    return {
        "item_id": row["item_id"], "text": text, "text_representation": row["text_representation"], "tone": tone,
        **values,
        "factual_calibration": "unverifiable",
        "benchmark_reference": "Not assessed: headline/post-only dictionary baseline; no release-time source verification.",
        "political_attribution_target": target, "political_valence": valence,
        "evidence_excerpt": clip_evidence(text, triggers or targets),
        "annotator_notes": "Machine-assisted dictionary baseline v1; requires independent human review.",
        "model_name": "dictionary_baseline_v1", "negative_triggers": "; ".join(negative), "positive_triggers": "; ".join(positive),
    }


def main() -> None:
    with INPUT.open(encoding="utf-8", newline="") as stream:
        labels = [label(row) for row in csv.DictReader(stream)]
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(labels[0])
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(labels)
    summary = {
        "model": "dictionary_baseline_v1", "records": len(labels),
        "tone_counts": dict(Counter(row["tone"] for row in labels)),
        "factual_calibration": "Every record is unverifiable because the baseline did not inspect original publication context or official releases.",
        "use": "Review aid and conventional classifier baseline only. Not an independent human annotation set.",
    }
    (OUT / "dictionary_baseline_v1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
