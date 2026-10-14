"""Collect a balanced historical TV-caption archive from Internet Archive.

The source panel intentionally balances four national networks and four local
stations.  Each accepted row is a dated broadcast with public caption snippets;
its model-assisted codes remain pending independent-label validation.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from label_corpus_baseline_v3 import label as dictionary_label

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "data" / "corpus" / "historical"
PANEL = HIST / "tvnews_source_panel.csv"
PLAN = HIST / "tvnews_collection_plan.csv"
RAW = HIST / "raw" / "historical_items.csv"
FIELDS = ["item_id", "published_at", "available_on", "source_domain", "source_stratum", "include_default", "is_duplicate", "suspected_automated", "tone", "frame_price_level", "salience_recession_risk", "factual_calibration", "url", "publisher_url", "text", "text_representation", "archive_source", "archive_record_id", "retrieved_at", "extraction_method", "license_or_terms_note"]
TOPIC = re.compile(r"\b(inflation|prices?|costs?|econom(?:y|ic)|jobs?|hiring|layoffs?|employment|unemployment|recession|growth|wages?|rent)\b", re.I)
PRICE = re.compile(r"\b(inflation|prices?|costs?|rent|groceries|gas(?:oline)?)\b", re.I)
RECESSION = re.compile(r"\b(recession|downturn|contraction|unemployment|layoffs?|job cuts?)\b", re.I)


class Captions(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.depth = 0; self.snippets: list[list[str]] = []; self.current: list[str] = []
    def handle_starttag(self, tag, attrs):
        if tag == "div" and "snipin" in (dict(attrs).get("class") or ""):
            self.depth = 1; self.current = []
        elif self.depth: self.depth += 1
    def handle_endtag(self, tag):
        if not self.depth: return
        self.depth -= 1
        if not self.depth and self.current: self.snippets.append(self.current)
    def handle_data(self, data):
        if self.depth: self.current.append(data)


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "FRE-GY-7871A academic research collector/1.0"})
    with urlopen(request, timeout=45) as response: return response.read()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def initialise(start: str, end: str) -> list[dict]:
    panel = [row for row in csv.DictReader(PANEL.open(encoding="utf-8", newline="")) if row["collection_enabled"] == "true"]
    return [{"month": str(month), "source_domain": source["source_domain"], "archive_contributor": source["archive_contributor"], "source_stratum": source["source_stratum"], "query_status": "not_started", "candidate_count": "", "accepted_count": "", "notes": ""} for month in pd.period_range(start, end, freq="M") for source in panel]


def search(month: str, contributor: str, cap: int) -> list[dict]:
    start = f"{month}-01T00:00:00Z"; end = (pd.Period(month, freq="M").end_time.strftime("%Y-%m-%dT23:59:59Z"))
    query = f"collection:tvarchive AND contributor:{contributor} AND date:[{start} TO {end}]"
    params = [("q", query), ("fl[]", "identifier"), ("fl[]", "date"), ("fl[]", "publicdate"), ("fl[]", "title"), ("output", "json"), ("rows", str(cap)), ("sort[]", "publicdate asc")]
    return json.loads(fetch("https://archive.org/advancedsearch.php?" + urlencode(params)).decode("utf-8"))["response"]["docs"]


def relevant_text(identifier: str) -> str:
    parser = Captions(); parser.feed(fetch(f"https://archive.org/details/{identifier}").decode("utf-8", errors="replace"))
    snippets = [re.sub(r"\s+", " ", html.unescape(" ".join(part))).strip() for part in parser.snippets]
    keep = [snippet for snippet in snippets if TOPIC.search(snippet)]
    return " ".join(keep)


def run(start: str, end: str, cap: int, sleep_seconds: float, max_tasks: int | None, plan_path: Path) -> dict:
    plan = list(csv.DictReader(plan_path.open(encoding="utf-8", newline=""))) if plan_path.exists() else initialise(start, end)
    existing = list(csv.DictReader(RAW.open(encoding="utf-8", newline=""))) if RAW.exists() else []
    write_csv(plan_path, plan, list(plan[0]))
    accepted_ids = {row["item_id"] for row in existing}; now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    added = 0
    processed = 0
    for number, task in enumerate(plan, 1):
        if max_tasks is not None and processed >= max_tasks: break
        if task["query_status"] == "complete": continue
        processed += 1
        try: candidates = search(task["month"], task["archive_contributor"], cap)
        except Exception as error:
            task.update(query_status="query_error", notes=type(error).__name__); continue
        task["candidate_count"] = str(len(candidates)); included = 0
        for item in candidates:
            item_id = f"iatv_{item['identifier']}"
            if item_id in accepted_ids: continue
            try: text = relevant_text(item["identifier"])
            except Exception: continue
            if len(text) < 250: continue
            coded = dictionary_label({"item_id": item_id, "text": text})
            detail_url = f"https://archive.org/details/{item['identifier']}"
            existing.append({"item_id": item_id, "published_at": item["date"], "available_on": item.get("publicdate") or item["date"], "source_domain": task["source_domain"], "source_stratum": task["source_stratum"], "include_default": "true", "is_duplicate": "false", "suspected_automated": "false", "tone": coded["tone"], "frame_price_level": "1" if PRICE.search(text) else "0", "salience_recession_risk": "1" if RECESSION.search(text) else "0", "factual_calibration": "unverifiable", "url": detail_url, "publisher_url": detail_url, "text": text, "text_representation": "internet_archive_tvnews_topic_caption_snippets", "archive_source": "Internet Archive TV News Archive", "archive_record_id": item["identifier"], "retrieved_at": now, "extraction_method": "Internet Archive advanced search + public details-page caption-snippet extraction; non-topic snippets omitted", "license_or_terms_note": "Internet Archive metadata and caption snippets; broadcast/caption rights remain with their owners. Retained only for reproducible academic research."})
            accepted_ids.add(item_id); included = 1; added += 1; break
        task.update(query_status="complete", accepted_count=str(included), notes="One topic-caption item retained when available; availability is Internet Archive publicdate.")
        if processed % 5 == 0: write_csv(RAW, existing, FIELDS); write_csv(plan_path, plan, list(plan[0]))
        time.sleep(sleep_seconds)
    write_csv(RAW, existing, FIELDS); write_csv(plan_path, plan, list(plan[0]))
    return {"planned_source_months": len(plan), "tasks_processed": processed, "new_items": added, "total_items": len(existing), "raw": str(RAW), "plan": str(plan_path)}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--start", default="2020-01"); parser.add_argument("--end", default="2024-12"); parser.add_argument("--candidate-cap", type=int, default=12); parser.add_argument("--sleep-seconds", type=float, default=0.15); parser.add_argument("--max-tasks", type=int); parser.add_argument("--plan", type=Path, default=PLAN)
    args = parser.parse_args(); print(json.dumps(run(args.start, args.end, args.candidate_cap, args.sleep_seconds, args.max_tasks, args.plan), indent=2))


if __name__ == "__main__": main()
