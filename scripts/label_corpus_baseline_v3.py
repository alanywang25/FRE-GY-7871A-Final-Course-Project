"""A conservative, transparent context-aware dictionary tone baseline."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "corpus" / "processed" / "balanced_analysis_sample.csv"
OUT = ROOT / "data" / "corpus" / "model_assisted"
OUTPUT = OUT / "dictionary_baseline_v3.csv"

POSITIVE = re.compile(r"\b(record (?:annual )?(?:profit|high)|blowout|bright|leading|freest|rebound|recovery|strong(?:er)?|rall(?:y|ies)|stocks? rise|jobs? (?:added|gains?)|hiring|expan(?:d|sion)|boost|improv(?:e|ed|ing)|growth)\b", re.I)
NEGATIVE = re.compile(r"\b(layoffs?|laid off|job cuts?|unemployment|recession|downturn|contraction|slump|loss(?:es)?|crisis|foreclos(?:ure|ing)|stagnat(?:e|ing)|sluggish|slowest|slow growth|depression|strangulation|backlash|squeez(?:e|ed)|frustrat(?:e|ed|ing)|high(?:er)? (?:prices?|costs?|inflation)|rising (?:prices?|costs?|inflation)|price pressure|cost pressure|inflation (?:risk|worr(?:y|ies)|pressure)|worries? about inflation|cautious)\b", re.I)
DISINFLATION = re.compile(r"\b(inflation (?:cooled|eased|slowed|fell|declined)|cool(?:ing|ed) inflation|eas(?:ing|ed) inflation)\b", re.I)
CONTRAST = re.compile(r"\b(but|while|however|even as|despite)\b", re.I)
SPAM_OR_BARE = re.compile(r"^\s*(?:#?inflation|#?economy|#?jobs?)\s*[.!?]*\s*$", re.I)


def label(row: dict) -> dict:
    text = row["text"].strip()
    positive = [match.group(0) for match in POSITIVE.finditer(text)]
    negative = [match.group(0) for match in NEGATIVE.finditer(text)]
    disinflation = [match.group(0) for match in DISINFLATION.finditer(text)]
    if SPAM_OR_BARE.match(text):
        tone = "neutral"
    elif (positive and negative) or (CONTRAST.search(text) and (positive or negative or disinflation)):
        tone = "mixed"
    elif negative:
        tone = "negative"
    elif positive or disinflation:
        tone = "positive"
    else:
        tone = "neutral"
    return {"item_id": row["item_id"], "tone": tone, "model_name": "dictionary_baseline_v3", "dictionary_evidence": "; ".join(negative + positive + disinflation)}


def main() -> None:
    with INPUT.open(encoding="utf-8", newline="") as stream:
        rows = list({row["item_id"]: row for row in csv.DictReader(stream)}.values())
    labels = [label(row) for row in rows]
    OUT.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(labels[0]))
        writer.writeheader()
        writer.writerows(labels)
    (OUT / "dictionary_baseline_v3_summary.json").write_text(json.dumps({"model": "dictionary_baseline_v3", "records": len(labels), "approach": "Transparent context-aware static rules. Generic inflation mentions are not negative without adverse context."}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
