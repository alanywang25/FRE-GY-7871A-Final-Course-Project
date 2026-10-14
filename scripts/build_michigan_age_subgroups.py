"""Build documented age-subgroup ICS records from Michigan demographic tables.

The public tables report Table 1A's Index of Consumer Sentiment (ICS) and its
subgroup-specific ``Cases`` count.  They are explicitly three-month moving
averages, not one-month subgroup estimates.
"""

from __future__ import annotations

import csv
import re
from calendar import monthrange
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "templates" / "michigan_subgroups.csv"
SUBINDICES = ROOT / "data" / "templates" / "michigan_subindices.csv"
START_YEAR = 2010
EXTRACTED_ON = "2026-10-14"
SOURCES = {
    "18-34": "https://data.sca.isr.umich.edu/get-demographic-table.php?g=age&d=a1834&y=2026&m=8&n=alln&p=m&f=pdf&k=8581604d0a9c6f8f922791911fb232e4c29305fac80381a7a1c068f4e2d02040",
    "35-54": "https://data.sca.isr.umich.edu/get-demographic-table.php?g=age&d=a3554&y=2026&m=8&n=alln&p=m&f=pdf&k=5e82363f28ee6125d33acef1dd9d82bed514fa0f537d33df60cbb8c8ebdc06f9",
    "55+": "https://data.sca.isr.umich.edu/get-demographic-table.php?g=age&d=a5597&y=2026&m=8&n=alln&p=m&f=pdf&k=0e42df59c1dab09b0d99008912c8b7071bd17f7c3253738e8ab67d39ac89b51e",
}
MONTHS = {
    name: number
    for number, name in enumerate(
        ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
        start=1,
    )
}
TABLE_ROW = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<year>\d{4})\s+(?P<ics>\d+(?:\.\d+)?)\s+(?P<cases>\d+)"
)
OUTPUT_FIELDS = (
    "month", "subgroup_dimension", "subgroup_value", "index_name", "index_value", "sample_size",
    "source_url", "release_timestamp", "vintage_id", "notes",
)


def parse_date(value: str) -> datetime:
    for pattern in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value}")


def release_dates() -> dict[tuple[int, int], str]:
    with SUBINDICES.open(newline="", encoding="utf-8") as handle:
        result = {}
        for row in csv.DictReader(handle):
            month = parse_date(row["month"])
            released = parse_date(row["release_timestamp"])
            result[(month.year, month.month)] = released.date().isoformat()
    return result


def table_1a_rows(url: str) -> list[tuple[int, int, float, int]]:
    document = urlopen(url, timeout=120).read()
    reader = PdfReader(BytesIO(document))
    # In the supplied tables, Table 1A occupies PDF pages 2–13.  Restricting
    # extraction prevents similarly shaped rows in later substantive tables.
    text = "\n".join(page.extract_text() or "" for page in reader.pages[1:13])
    rows = []
    for match in TABLE_ROW.finditer(text):
        year = int(match.group("year"))
        if year < START_YEAR:
            continue
        rows.append((year, MONTHS[match.group("month")], float(match.group("ics")), int(match.group("cases"))))
    return rows


def main() -> None:
    releases = release_dates()
    output_rows: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for group, url in SOURCES.items():
        values = table_1a_rows(url)
        seen = set()
        for year, month_number, index_value, cases in values:
            key = (year, month_number)
            if key in seen:
                continue
            seen.add(key)
            if key not in releases:
                raise RuntimeError(f"Missing endpoint final-release date for {year}-{month_number:02d}")
            month_end = monthrange(year, month_number)[1]
            output_rows.append({
                "month": f"{year}-{month_number:02d}-{month_end:02d}",
                "subgroup_dimension": "age",
                "subgroup_value": group,
                "index_name": "ICS",
                "index_value": f"{index_value:.1f}",
                "sample_size": str(cases),
                "source_url": url,
                "release_timestamp": releases[key],
                "vintage_id": f"{year}-{month_number:02d}-final-age-3m-ics",
                "notes": (
                    "Michigan demographic Table 1A: ICS is a three-month moving average. "
                    "Published Cases is retained as source metadata and is not asserted to be the "
                    "pooled analytic base for that moving average. Endpoint final-release date "
                    f"joined from the Michigan final-release schedule; table extracted {EXTRACTED_ON}."
                ),
            })
        counts[group] = len(seen)

    expected = set(releases)
    if any(counts[group] != len(expected) for group in SOURCES):
        raise RuntimeError(f"Incomplete age table coverage: {counts}; expected {len(expected)} each")
    output_rows.sort(key=lambda row: (row["month"], row["subgroup_value"]))
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Wrote {len(output_rows)} rows: {counts}")


if __name__ == "__main__":
    main()
