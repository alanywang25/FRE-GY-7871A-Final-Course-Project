"""Train an inspectable weighted-keyword tone dictionary with OOF predictions."""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "corpus" / "independent_validation" / "adjudication" / "independent_tone_adjudications.csv"
OUT = ROOT / "data" / "corpus" / "model_assisted"
OOF = OUT / "dictionary_baseline_v2_oof.csv"
FULL = OUT / "dictionary_baseline_v2.csv"
MODEL = OUT / "dictionary_baseline_v2_model.json"
TOKEN = re.compile(r"[a-z][a-z0-9']+", re.I)
CLASSES = ("mixed", "negative", "neutral", "positive")


def tokens(text: str) -> list[str]:
    words = TOKEN.findall(text.lower())
    unigrams = [word for word in words if len(word) > 1]
    bigrams = [f"{left} {right}" for left, right in zip(unigrams, unigrams[1:])]
    return unigrams + bigrams


def fit(rows: list[dict[str, str]]) -> dict:
    counts = {label: Counter() for label in CLASSES}
    documents = Counter()
    for row in rows:
        label = row["tone"]
        documents[label] += 1
        counts[label].update(tokens(row["text"]))
    vocabulary = sorted(set().union(*(set(values) for values in counts.values())))
    alpha = 1.0
    total_docs = sum(documents.values())
    return {
        "classes": list(CLASSES), "alpha": alpha, "vocabulary_size": len(vocabulary),
        "documents": dict(documents), "token_counts": {label: dict(counts[label]) for label in CLASSES},
        "token_totals": {label: sum(counts[label].values()) for label in CLASSES}, "total_documents": total_docs,
    }


def predict_text(text: str, model: dict) -> tuple[str, list[str]]:
    features = tokens(text)
    scores: dict[str, float] = {}
    contributions: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for label in model["classes"]:
        documents = model["documents"].get(label, 0)
        score = math.log((documents + 1) / (model["total_documents"] + len(model["classes"])))
        denominator = model["token_totals"][label] + model["alpha"] * model["vocabulary_size"]
        for token in features:
            count = model["token_counts"][label].get(token, 0)
            contribution = math.log((count + model["alpha"]) / denominator)
            score += contribution
            if count:
                contributions[label].append((contribution, token))
        scores[label] = score
    prediction = max(model["classes"], key=lambda label: (scores[label], label))
    evidence = [token for _, token in sorted(contributions[prediction], reverse=True)[:5]]
    return prediction, evidence


def fold_index(item_id: str, label: str, rank: dict[str, int]) -> int:
    return rank[f"{label}:{item_id}"] % 5


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    with LABELS.open(encoding="utf-8", newline="") as stream:
        rows = [
            {"item_id": row["item_id"], "text": row["text"], "tone": row["adjudicated_tone"]}
            for row in csv.DictReader(stream)
            if row["adjudication_status"] in {"independent_consensus", "independent_manual_adjudication"} and row["adjudicated_tone"]
        ]
    ranks = {f"{row['tone']}:{row['item_id']}": index for index, row in enumerate(sorted(rows, key=lambda row: (row["tone"], row["item_id"]))) }
    oof_rows = []
    for fold in range(5):
        train = [row for row in rows if fold_index(row["item_id"], row["tone"], ranks) != fold]
        model = fit(train)
        for row in rows:
            if fold_index(row["item_id"], row["tone"], ranks) == fold:
                tone, evidence = predict_text(row["text"], model)
                oof_rows.append({"item_id": row["item_id"], "tone": tone, "model_name": "weighted_dictionary_v2_oof", "dictionary_evidence": "; ".join(evidence), "fold": str(fold)})
    full_model = fit(rows)
    full_rows = []
    for row in rows:
        tone, evidence = predict_text(row["text"], full_model)
        full_rows.append({"item_id": row["item_id"], "tone": tone, "model_name": "weighted_dictionary_v2", "dictionary_evidence": "; ".join(evidence)})
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OOF, sorted(oof_rows, key=lambda row: row["item_id"]))
    write_csv(FULL, sorted(full_rows, key=lambda row: row["item_id"]))
    MODEL.write_text(json.dumps(full_model, indent=2), encoding="utf-8")
    summary = {
        "model": "weighted_dictionary_v2", "records": len(rows), "evaluation": "five-fold stratified out-of-fold predictions", 
        "interpretation": "Transparent multinomial weighted-token dictionary. The stored model contains every learned unigram/bigram count and class prior.",
    }
    (OUT / "dictionary_baseline_v2_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
