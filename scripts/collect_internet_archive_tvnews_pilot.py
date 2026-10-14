"""Collect a small, separately identified Internet Archive TV News pilot.

This deliberately writes outside ``raw/historical_items.csv``: broadcast
captions are a different media modality from the planned web-news panel and
need an explicit methodological decision before they are pooled.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from label_corpus_baseline_v3 import label as dictionary_label

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "corpus" / "historical" / "pilots" / "internet_archive_tvnews_pilot.csv"
FIELDS = [
    "item_id", "published_at", "available_on", "source_domain", "source_stratum",
    "include_default", "is_duplicate", "suspected_automated", "tone", "frame_price_level",
    "salience_recession_risk", "factual_calibration", "url", "publisher_url", "text",
    "text_representation", "archive_source", "archive_record_id", "retrieved_at",
    "extraction_method", "license_or_terms_note",
]
TOPIC = re.compile(r"\b(inflation|prices?|costs?|econom(?:y|ic)|jobs?|hiring|layoffs?|employment|unemployment|recession|growth|wages?|rent)\b", re.I)
PRICE = re.compile(r"\b(inflation|prices?|costs?|rent|groceries|gas(?:oline)?)\b", re.I)
RECESSION = re.compile(r"\b(recession|downturn|contraction|unemployment|layoffs?|job cuts?)\b", re.I)


class Captions(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and "snipin" in (dict(attrs).get("class") or ""):
            self.depth += 1
        elif self.depth:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.depth:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "FRE-GY-7871A academic research collector/1.0"})
    with urlopen(request, timeout=45) as response:
        return response.read()


def collect(month: str, station: str, source_domain: str, source_stratum: str, limit: int) -> list[dict]:
    start, end = f"{month}-01T00:00:00Z", f"{month}-31T23:59:59Z"
    query = f"collection:tvarchive AND contributor:{station} AND date:[{start} TO {end}]"
    params = urlencode([( "q", query), ("fl[]", "identifier"), ("fl[]", "date"), ("fl[]", "publicdate"), ("fl[]", "title"), ("output", "json"), ("rows", str(limit))])
    records = json.loads(fetch(f"https://archive.org/advancedsearch.php?{params}").decode("utf-8"))["response"]["docs"]
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output = []
    for record in records:
        identifier = record["identifier"]
        details_url = f"https://archive.org/details/{identifier}"
        parser = Captions()
        parser.feed(fetch(details_url).decode("utf-8", errors="replace"))
        text = re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()
        if len(text) < 500 or not TOPIC.search(text):
            continue
        title = record.get("title", "")
        coded = dictionary_label({"item_id": identifier, "text": f"{title}. {text}"})
        output.append({
            "item_id": f"iatv_{identifier}", "published_at": record["date"], "available_on": record.get("publicdate") or record["date"],
            "source_domain": source_domain, "source_stratum": source_stratum, "include_default": "true", "is_duplicate": "false", "suspected_automated": "false",
            "tone": coded["tone"], "frame_price_level": "1" if PRICE.search(text) else "0", "salience_recession_risk": "1" if RECESSION.search(text) else "0",
            "factual_calibration": "unverifiable", "url": details_url, "publisher_url": details_url, "text": f"{title}. {text}",
            "text_representation": "internet_archive_tvnews_caption_snippets", "archive_source": "Internet Archive TV News Archive", "archive_record_id": identifier,
            "retrieved_at": now, "extraction_method": "Internet Archive advanced search + public details-page caption-snippet extraction",
            "license_or_terms_note": "Internet Archive item metadata and caption snippets; broadcast/caption rights remain with their owners. Retained only as a reproducible academic-research pilot.",
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", default="2020-01")
    parser.add_argument("--station", default="CNNW")
    parser.add_argument("--source-domain", default="cnn.com")
    parser.add_argument("--source-stratum", default="national", choices=["national", "local"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows = collect(args.month, args.station, args.source_domain, args.source_stratum, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"month": args.month, "station": args.station, "accepted_items": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
