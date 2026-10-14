"""Replace annual-backfill availability dates with Michigan's original final dates.

The historical release-date PDF records dates, rather than times of day.  This
script retains each row's result-report URL (the evidence for the index values)
and records the exact final-release *date* in ``release_timestamp``.
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from pypdf import PdfReader


DEFAULT_INPUT = Path("data/templates/michigan_subindices.csv")
RELEASE_DATES_URL = "https://data.sca.isr.umich.edu/fetchdoc.php?docid=75443"
MONTH_NUMBERS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
ROW_PATTERN = re.compile(
    r"(?P<month>[A-Z][a-z]{2})\s+(?P<year>\d{4})\s+"
    r"(?P<prelim>\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(?P<final>\d{1,2}/\d{1,2}/\d{4})"
)


def parse_month(value: str) -> datetime:
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unsupported month format: {value!r}")


def parse_release_dates(url: str) -> dict[tuple[int, int], datetime]:
    pdf = PdfReader(BytesIO(urlopen(url, timeout=60).read()))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    dates: dict[tuple[int, int], datetime] = {}
    for match in ROW_PATTERN.finditer(text):
        year = int(match.group("year"))
        month = MONTH_NUMBERS[match.group("month")]
        dates[(year, month)] = datetime.strptime(match.group("final"), "%m/%d/%Y")
    return dates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--release-dates-url", default=RELEASE_DATES_URL)
    args = parser.parse_args()

    release_dates = parse_release_dates(args.release_dates_url)
    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = handle.seek(0) or next(csv.reader(handle))

    updated = 0
    for row in rows:
        observation_month = parse_month(row["month"])
        if not 2010 <= observation_month.year <= 2025:
            continue
        final_date = release_dates.get((observation_month.year, observation_month.month))
        if final_date is None:
            raise RuntimeError(f"No final release date for {observation_month:%Y-%m}")
        row["release_timestamp"] = f"{final_date.month}/{final_date.day}/{final_date:%y}"
        row["vintage_id"] = f"{observation_month:%Y-%m}-final"
        row["notes"] = (
            "Final value transcribed from the annual December final-result report; "
            "original final-release date from University of Michigan Historical "
            f"Prelim/Final Release Dates ({args.release_dates_url}; date only)."
        )
        updated += 1

    if updated != 192:
        raise RuntimeError(f"Expected 192 historical rows to update, updated {updated}")
    with args.input.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Updated {updated} rows in {args.input}")


if __name__ == "__main__":
    main()
