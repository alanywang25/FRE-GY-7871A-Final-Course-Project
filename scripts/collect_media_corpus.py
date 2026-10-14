"""Collect a documented, rate-limited headline corpus and public social supplement.

The script stores only headline/news-card text and public post text. It does not
scrape article bodies or claim to measure exposure. Run it with network access.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"
OUTPUT = CORPUS / "processed"
REGISTRY = CORPUS / "source_registry.csv"
NEWS_PER_SOURCE = 25
NEWS_WINDOW_DAYS = 60
SOCIAL_TAGS = ("economy", "inflation", "jobs")
SOCIAL_PAGES_PER_TAG = 3
KEYWORDS = ("economy", "economic", "inflation", "unemployment", "job", "wage", "layoff", "price", "cost of living", "gdp", "growth", "recession")
TOPIC_PATTERN = re.compile(r"\b(?:economy|economic|inflation|unemployment|jobs?|wages?|layoffs?|prices?|gdp|growth|recession)\b|cost of living", re.I)
USER_AGENT = "AcademicMediaCorpus/1.0 (course project; contact: local-course-project)"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_html(value: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or ""))).strip()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml,application/json,text/plain,*/*"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def google_news_url(domain: str) -> tuple[str, str]:
    query = f'({" OR ".join(KEYWORDS)}) site:{domain} when:{NEWS_WINDOW_DAYS}d'
    params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return f"https://news.google.com/rss/search?{params}", query


def collect_news(source: dict, retrieved_at: str) -> list[dict]:
    feed_url, query = google_news_url(source["domain"])
    root = ET.fromstring(fetch(feed_url))
    output: list[dict] = []
    for item in root.findall("./channel/item"):
        title = clean_html(item.findtext("title", ""))
        card_url = item.findtext("link", "")
        source_node = item.find("source")
        returned_domain = "" if source_node is None else source_node.attrib.get("url", "")
        returned_name = "" if source_node is None else (source_node.text or "").strip()
        # Search engines may return syndications. Keep only the requested publisher domain.
        if source["domain"] not in returned_domain:
            continue
        # The unit is a headline/card, so headline relevance must be visible in
        # the stored text rather than inferred from an unavailable article body.
        if not TOPIC_PATTERN.search(title):
            continue
        if returned_name and title.endswith(f" - {returned_name}"):
            title = title[: -(len(returned_name) + 3)].rstrip()
        published = item.findtext("pubDate", "")
        try:
            published = parsedate_to_datetime(published).astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except (TypeError, ValueError):
            pass
        output.append({
            "item_id": stable_id("news", card_url), "platform": "google_news_rss", "item_type": "headline_card",
            "source_name": returned_name or source["source_name"], "source_domain": source["domain"],
            "source_stratum": source["stratum"], "geography": source["geography"], "market": source["market"],
            "published_at": published, "retrieved_at": retrieved_at, "language": "en", "text": title,
            "url": card_url, "publisher_url": returned_domain, "query": query, "query_url": feed_url,
            "text_representation": "headline/news-card", "engagement_replies": "", "engagement_reposts": "",
            "engagement_favourites": "", "suspected_automated": False, "privacy_minimized": True,
        })
    return output[:NEWS_PER_SOURCE]


def collect_mastodon(tag: str, retrieved_at: str) -> list[dict]:
    output: list[dict] = []
    max_id = ""
    for _page in range(SOCIAL_PAGES_PER_TAG):
        params = {"limit": 40}
        if max_id:
            params["max_id"] = max_id
        url = f"https://mastodon.social/api/v1/timelines/tag/{urllib.parse.quote(tag)}?{urllib.parse.urlencode(params)}"
        payload = json.loads(fetch(url).decode("utf-8"))
        if not payload:
            break
        for post in payload:
            text = clean_html(post.get("content", ""))
            if post.get("reblog") is not None or (post.get("language") and post["language"] != "en"):
                continue
            if not TOPIC_PATTERN.search(text):
                continue
            account = post.get("account") or {}
            output.append({
                "item_id": stable_id("mastodon", str(post.get("id", ""))), "platform": "mastodon.social", "item_type": "public_post",
                "source_name": "Mastodon public hashtag timeline", "source_domain": "mastodon.social", "source_stratum": "social",
                "geography": "unknown", "market": "", "published_at": post.get("created_at", ""), "retrieved_at": retrieved_at,
                "language": post.get("language") or "unknown", "text": text, "url": post.get("url", ""), "publisher_url": "",
                "query": f"hashtag:{tag}", "query_url": url, "text_representation": "post", "engagement_replies": post.get("replies_count", 0),
                "engagement_reposts": post.get("reblogs_count", 0), "engagement_favourites": post.get("favourites_count", 0),
                "suspected_automated": bool(account.get("bot", False)), "privacy_minimized": True,
                "author_id_hash": stable_id("account", str(account.get("id", ""))),
            })
        next_id = str(payload[-1].get("id", ""))
        if not next_id or next_id == max_id:
            break
        max_id = next_id
        time.sleep(0.7)
    return output


def flag_duplicates(rows: list[dict]) -> None:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        key = stable_id("text", normalized(row["text"]))
        groups.setdefault(key, []).append(row)
    for key, group in groups.items():
        for row in group:
            row["duplicate_group_id"] = key
            row["is_duplicate"] = len(group) > 1
            first_in_group = row["item_id"] == min(x["item_id"] for x in group)
            row["include_default"] = (not row["is_duplicate"] or first_in_group) and not row["suspected_automated"]


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def balanced_sample(rows: list[dict]) -> list[dict]:
    """Create equal national/local/social strata without discarding the full corpus.

    Within news strata, round-robin selection across publisher domains limits a
    prolific publisher's influence. Within the social stratum it round-robins
    across the three query tags. It is a content-supply sample, never exposure.
    """
    eligible = [row.copy() for row in rows if row["include_default"]]
    counts = {stratum: sum(row["source_stratum"] == stratum for row in eligible) for stratum in ("national", "local", "social")}
    target = min(counts.values())
    chosen: list[dict] = []
    for stratum in ("national", "local", "social"):
        group = [row for row in eligible if row["source_stratum"] == stratum]
        bucket_key = "query" if stratum == "social" else "source_domain"
        buckets: dict[str, list[dict]] = {}
        for row in sorted(group, key=lambda item: (item["published_at"], item["item_id"]), reverse=True):
            buckets.setdefault(str(row[bucket_key]), []).append(row)
        while len([row for row in chosen if row["source_stratum"] == stratum]) < target and any(buckets.values()):
            for key in sorted(buckets):
                if buckets[key] and len([row for row in chosen if row["source_stratum"] == stratum]) < target:
                    row = buckets[key].pop(0)
                    row["analysis_sample"] = True
                    chosen.append(row)
    return chosen


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    retrieved_at = now()
    with REGISTRY.open(encoding="utf-8", newline="") as stream:
        sources = list(csv.DictReader(stream))
    rows: list[dict] = []
    run_log: list[dict] = []
    for index, source in enumerate(sources):
        try:
            batch = collect_news(source, retrieved_at)
            rows.extend(batch)
            run_log.append({"kind": "news", "source": source["source_name"], "status": "ok", "retained": len(batch)})
        except Exception as error:  # retain failures rather than silently changing composition
            run_log.append({"kind": "news", "source": source["source_name"], "status": "failed", "retained": 0, "error": str(error)[:300]})
        if index < len(sources) - 1:
            time.sleep(0.25)
    for tag in SOCIAL_TAGS:
        try:
            batch = collect_mastodon(tag, retrieved_at)
            rows.extend(batch)
            run_log.append({"kind": "social", "source": f"Mastodon #{tag}", "status": "ok", "retained": len(batch)})
        except Exception as error:
            run_log.append({"kind": "social", "source": f"Mastodon #{tag}", "status": "failed", "retained": 0, "error": str(error)[:300]})
        time.sleep(0.25)
    flag_duplicates(rows)
    write_csv(OUTPUT / "media_corpus.csv", rows)
    included = [r for r in rows if r["include_default"]]
    sample = balanced_sample(rows)
    write_csv(OUTPUT / "balanced_analysis_sample.csv", sample)
    by_stratum = {s: sum(r["source_stratum"] == s and r["include_default"] for r in rows) for s in ("national", "local", "social")}
    summary = {"retrieved_at": retrieved_at, "window_days": NEWS_WINDOW_DAYS, "headline_cap_per_news_source": NEWS_PER_SOURCE, "records_collected": len(rows), "records_default_included": len(included), "included_by_stratum": by_stratum, "balanced_analysis_sample_records": len(sample), "balanced_sample_by_stratum": {s: sum(r["source_stratum"] == s for r in sample) for s in ("national", "local", "social")}, "source_run_log": run_log, "notes": ["News records are headline/news-card observations, not full articles.", "Social records are public Mastodon tag results and are not representative of exposure.", "Duplicate records are retained and flagged. Suspected automated posts are retained but excluded from the default and balanced samples. Do not infer exposure from engagement."]}
    (OUTPUT / "collection_manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
