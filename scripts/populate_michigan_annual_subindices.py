"""Backfill Michigan subindices from the supplied annual December reports.

Each report contains a 13-observation table: the prior December followed by
January--December of its report year.  This script retains the report's actual
publication date for every extracted value.  It therefore creates a transparent
historical *backfill* and does not misrepresent earlier months as having been
available on their individual original release dates.
"""
from __future__ import annotations

import csv
import re
from calendar import monthrange
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "templates" / "michigan_subindices.csv"
REPORTS = {
    2010: 41633, 2011: 43603, 2012: 46694, 2013: 49061,
    2014: 51834, 2015: 54371, 2016: 57270, 2017: 59549,
    2018: 61836, 2019: 64466, 2020: 66719, 2021: 69091,
    2022: 71962, 2023: 74601, 2024: 77763, 2025: 80322,
}
FIELDS = [
    "month", "current_conditions", "expectations", "source_url",
    "release_timestamp", "vintage_id", "notes",
]


def report_text(url: str) -> str:
    """Fetch and extract the one-page report while preserving table spacing."""
    with urlopen(url, timeout=30) as response:
        content = response.read()
    with pdfplumber.open(BytesIO(content)) as pdf:
        return "\n".join(
            page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            for page in pdf.pages
        )


def parse_series(text: str, label: str, following_label: str) -> list[float]:
    match = re.search(
        rf"{re.escape(label)}\s+(.+?)\s+{re.escape(following_label)}",
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError(f"Could not locate {label!r} table row.")
    values = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", match.group(1))]
    if len(values) != 13:
        raise ValueError(f"Expected 13 {label!r} values; found {len(values)}: {values}")
    return values


def parse_release_date(text: str, year: int) -> str:
    candidates = re.findall(
        r"(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},\s+20\d{2}",
        text,
    )
    for candidate in candidates:
        parsed = datetime.strptime(candidate, "%B %d, %Y").date()
        if parsed.year == year:
            return parsed.isoformat()
    raise ValueError(f"Could not identify the {year} report date.")


def main() -> None:
    with OUTPUT.open(newline="", encoding="utf-8") as stream:
        existing = list(csv.DictReader(stream))

    rows_by_month = {row["month"]: row for row in existing}
    for year, document_id in REPORTS.items():
        url = f"https://data.sca.isr.umich.edu/fetchdoc.php?docid={document_id}"
        text = report_text(url)
        current = parse_series(text, "Current Economic Conditions", "Index of Consumer Expectations")
        expectations = parse_series(text, "Index of Consumer Expectations", "Index Components")
        release_date = parse_release_date(text, year)
        for month_number, (current_value, expectation_value) in enumerate(
            zip(current[1:], expectations[1:]), start=1
        ):
            month = f"{year}-{month_number:02d}-{monthrange(year, month_number)[1]:02d}"
            rows_by_month[month] = {
                "month": month,
                "current_conditions": f"{current_value:.1f}",
                "expectations": f"{expectation_value:.1f}",
                "source_url": url,
                "release_timestamp": release_date,
                "vintage_id": f"{year}-{month_number:02d}-final-annual-backfill",
                "notes": (
                    "Final value transcribed from the annual December final-result "
                    "report; release date is that report's publication date, not the "
                    "original monthly availability date."
                ),
            }

    rows = sorted(rows_by_month.values(), key=lambda row: row["month"])
    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
