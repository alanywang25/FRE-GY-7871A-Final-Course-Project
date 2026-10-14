"""Add compact, provisional benchmark citations to the annotation packets.

The corpus retains headlines/posts rather than verified full articles and release
snapshots. These references are therefore retrieval aids, not factual verdicts.
All existing ``unverifiable`` calibration labels are deliberately preserved.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "corpus" / "processed" / "balanced_analysis_sample.csv"
PACKETS = [
    ROOT / "data" / "corpus" / "labeling" / "annotator_a.csv",
    ROOT / "data" / "corpus" / "labeling" / "annotator_b.csv",
]


def candidate(text: str) -> tuple[str, str] | None:
    value = re.sub(r"https?://\S+|\b[\w.-]+\.(?:com|org|gov|gy)\S*", "", text.casefold())
    rules = [
        (("cpi", "consumer price index"), "BLS CPI", "https://www.bls.gov/cpi/"),
        (("pce", "personal income", "disposable income", "gdp", "gross domestic product"), "BEA release tables", "https://www.bea.gov/news/"),
        (("unemployment", "jobs report", "employment", "payroll", "wage", "layoff", "hiring"), "BLS Employment Situation", "https://www.bls.gov/news.release/empsit.htm"),
        (("statcan", "canada"), "Statistics Canada releases", "https://www.statcan.gc.ca/"),
        (("fomc", "federal reserve", "interest rate", "rate hike", "rate cut"), "Federal Reserve FOMC statements", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
        (("diesel", "gas price", "gasoline", "crude oil", "wti", "oil price"), "EIA petroleum prices", "https://www.eia.gov/petroleum/"),
        (("consumer sentiment", "michigan survey"), "University of Michigan Surveys of Consumers", "https://data.sca.isr.umich.edu/"),
        (("world bank",), "World Bank data/releases", "https://www.worldbank.org/"),
        (("imf",), "IMF data/releases", "https://www.imf.org/"),
        (("wto",), "WTO statistics/releases", "https://www.wto.org/"),
    ]
    for words, name, url in rules:
        if any(word in value for word in words):
            return name, url
    return None


def compact_reference(item: dict[str, str]) -> str:
    date = (item.get("published_at") or "")[:10] or "date unavailable"
    source = item.get("source_name") or item.get("source_domain") or "source unavailable"
    match = candidate(item.get("text", ""))
    if match:
        name, url = match
        return f"Unverified; candidate benchmark: {name}, {url}; item source: {source}, {date}."
    kind = item.get("text_representation") or "retained text"
    return f"Unverifiable from retained {kind}; item source: {source}, {date}; no release-time benchmark identified."


def main() -> None:
    with SAMPLE.open(encoding="utf-8", newline="") as stream:
        items = {row["item_id"]: row for row in csv.DictReader(stream)}
    for packet in PACKETS:
        with packet.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
        for row in rows:
            row["benchmark_reference"] = compact_reference(items[row["item_id"]])
        with packet.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Updated {packet.name}: {len(rows)} provisional benchmark references")


if __name__ == "__main__":
    main()
