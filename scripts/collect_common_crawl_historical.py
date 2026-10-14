"""Build a conservative, availability-dated historical media archive from Common Crawl.

The collector processes the existing source-month plan.  It accepts an item only
when a Common Crawl WARC response can be retrieved, its publisher metadata has
an explicit publication date in the plan month, and the extracted article text
is both substantial and relevant to the project economic topic.  It records
the Crawl timestamp as ``available_on`` (a deliberately conservative proxy for
the first point at which this public archive could have supported coding).

This is a reproducible *model-assisted intake*, not independent human coding.
All tone/frame fields must receive the project's independent-label validation
before the resulting monthly series is used for effect estimation.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from label_corpus_baseline_v3 import label as dictionary_label

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "data" / "corpus" / "historical"
PLAN = HISTORICAL / "collection_plan.csv"
OUTPUT = HISTORICAL / "raw" / "historical_items.csv"
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
META_DATE = re.compile(
    r"<(?:meta|time)[^>]+(?:property|name|itemprop|datetime)=[\"'](?:article:published_time|datePublished|date|publishdate|pubdate|datepublished)[\"'][^>]+(?:content|datetime)=[\"']([^\"']+)",
    re.I,
)
TITLE = re.compile(r"<(?:meta)[^>]+(?:property|name)=[\"'](?:og:title|twitter:title)[\"'][^>]+content=[\"']([^\"']+)", re.I)
TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def get_json(url: str, timeout: int = 45) -> object:
    request = Request(url, headers={"User-Agent": "FRE-GY-7871A academic research collector/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json_lines(url: str, timeout: int = 45) -> list[dict]:
    request = Request(url, headers={"User-Agent": "FRE-GY-7871A academic research collector/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return [json.loads(line) for line in response.read().decode("utf-8").splitlines() if line.strip()]


def get_bytes(url: str, offset: int, length: int, timeout: int = 45) -> bytes:
    request = Request(url, headers={"Range": f"bytes={offset}-{offset + length - 1}", "User-Agent": "FRE-GY-7871A academic research collector/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def as_iso(value: str) -> str | None:
    value = html.unescape(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_html(warc_bytes: bytes) -> tuple[str, str | None, str | None]:
    """Return cleaned article-ish text, publication date, and title from a WARC record."""
    try:
        payload = gzip.GzipFile(fileobj=io.BytesIO(warc_bytes)).read()
    except OSError:
        return "", None, None
    parts = payload.split(b"\r\n\r\n", 2)
    if len(parts) < 3:
        return "", None, None
    raw_html = parts[2].decode("utf-8", errors="replace")
    publication = next((as_iso(match) for match in META_DATE.findall(raw_html) if as_iso(match)), None)
    title_match = TITLE.search(raw_html)
    title = html.unescape(title_match.group(1)).strip() if title_match else None
    main_match = re.search(r"<article\b[^>]*>(.*?)</article>", raw_html, re.I | re.S)
    candidate = main_match.group(1) if main_match else raw_html
    candidate = re.sub(r"<(?:script|style|noscript|svg|nav|footer|header)\b[^>]*>.*?</(?:script|style|noscript|svg|nav|footer|header)>", " ", candidate, flags=re.I | re.S)
    text = html.unescape(TAG.sub(" ", candidate))
    return SPACE.sub(" ", text).strip(), publication, title


def index_for_month(indexes: list[dict], month: str) -> dict | None:
    start = pd.Timestamp(f"{month}-01", tz="UTC")
    end = start + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1)
    choices = []
    for index in indexes:
        crawl_start = pd.Timestamp(index["from"], tz="UTC")
        crawl_end = pd.Timestamp(index["to"], tz="UTC")
        if crawl_start < end and crawl_end >= start:
            choices.append(index)
    return min(choices, key=lambda item: item["from"]) if choices else None


def candidates(index: dict, domain: str, cap: int) -> list[dict]:
    params = urlencode({"url": domain, "matchType": "domain", "output": "json", "filter": ["status:200", "mime:text/html"], "limit": cap}, doseq=True)
    return get_json_lines(f"{index['cdx-api']}?{params}")


def run(plan_path: Path, output: Path, max_items_per_task: int, candidate_cap: int, resume: bool, max_tasks: int | None, start_at: int) -> dict:
    plan = list(csv.DictReader(plan_path.open(encoding="utf-8", newline="")))
    existing = list(csv.DictReader(output.open(encoding="utf-8", newline=""))) if resume and output.exists() else []
    seen_urls = {row["url"] for row in existing}
    indexes = get_json("https://index.commoncrawl.org/collinfo.json")
    if not isinstance(indexes, list):
        raise RuntimeError("Common Crawl index listing was not a JSON list.")
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    accepted, failures = list(existing), []
    processed = 0
    for number, task in enumerate(plan, start=1):
        if number < start_at:
            continue
        if max_tasks is not None and processed >= max_tasks:
            break
        processed += 1
        if task["query_status"] == "complete" and resume:
            continue
        index = index_for_month(indexes, task["month"])
        if not index:
            task.update(query_status="no_overlapping_crawl", candidate_count="0", accepted_count="0")
            continue
        try:
            found = candidates(index, task["source_domain"], candidate_cap)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            task.update(query_status="index_error", candidate_count="", accepted_count="0", notes=f"{index['id']}: {type(error).__name__}")
            failures.append(f"{task['month']} {task['source_domain']}: {type(error).__name__}")
            continue
        task["candidate_count"] = str(len(found))
        included = 0
        for record in found:
            if included >= max_items_per_task or record.get("url") in seen_urls:
                continue
            try:
                text, published_at, title = extract_html(get_bytes(f"https://data.commoncrawl.org/{record['filename']}", int(record["offset"]), int(record["length"])))
            except (HTTPError, URLError, TimeoutError, KeyError, ValueError):
                continue
            if not published_at or not published_at.startswith(task["month"]) or len(text) < 500 or not TOPIC.search(text):
                continue
            display_text = f"{title}. {text}" if title and title.lower() not in text.lower() else text
            coded = dictionary_label({"item_id": "", "text": display_text})
            record_id = f"{index['id']}:{record['filename']}:{record['offset']}:{record['length']}"
            item_id = "cc_" + hashlib.sha256(record_id.encode()).hexdigest()[:20]
            accepted.append({
                "item_id": item_id, "published_at": published_at, "available_on": pd.Timestamp(record["timestamp"], tz="UTC").isoformat().replace("+00:00", "Z"),
                "source_domain": task["source_domain"], "source_stratum": task["source_stratum"],
                "include_default": "true", "is_duplicate": "false", "suspected_automated": "false",
                "tone": coded["tone"], "frame_price_level": "1" if PRICE.search(display_text) else "0",
                "salience_recession_risk": "1" if RECESSION.search(display_text) else "0", "factual_calibration": "unverifiable",
                "url": record["url"], "publisher_url": record["url"], "text": display_text, "text_representation": "common_crawl_warc_html_text",
                "archive_source": "Common Crawl", "archive_record_id": record_id, "retrieved_at": retrieved_at,
                "extraction_method": "Common Crawl CDX index + byte-range WARC retrieval; publisher metadata date and HTML article-text extraction",
                "license_or_terms_note": "Public Common Crawl archive record; underlying publisher content remains subject to publisher terms and applicable copyright. Retained here for academic research and reproducibility.",
            })
            seen_urls.add(record["url"])
            included += 1
        task.update(query_status="complete" if included else "no_eligible_article", accepted_count=str(included), notes=f"Index {index['id']}; candidate cap={candidate_cap}; accepted records require in-month publisher metadata date and topical text.")
        if number % 25 == 0:
            print(f"processed {number}/{len(plan)} tasks; accepted {len(accepted) - len(existing)}")
        time.sleep(0.1)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(accepted)
    # A bounded run is diagnostic only; it must not make the operational plan
    # look complete or unavailable based on a transient archive response.
    if max_tasks is None:
        with plan_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(plan[0]))
            writer.writeheader()
            writer.writerows(plan)
    return {"tasks_planned": len(plan), "tasks_processed": processed, "accepted_items": len(accepted), "new_items": len(accepted) - len(existing), "failures": failures[:25], "output": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--max-items-per-task", type=int, default=1)
    parser.add_argument("--candidate-cap", type=int, default=100)
    parser.add_argument("--max-tasks", type=int, help="Bound a diagnostic or pilot run; omit to process the full plan.")
    parser.add_argument("--start-at", type=int, default=1, help="One-based source-month task position; useful for a bounded retry.")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.plan, args.output, args.max_items_per_task, args.candidate_cap, not args.no_resume, args.max_tasks, args.start_at), indent=2))


if __name__ == "__main__":
    main()
