"""Train a transparent conventional all-field classifier on development labels only."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from build_full_field_validation_packets import CODE_FIELDS


ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data/corpus/full_field_validation/adjudication/full_field_adjudicated_labels.csv"
OUT = ROOT / "data/corpus/model_assisted"
PREDICTIONS = OUT / "naive_bayes_full_field_predictions.csv"
MODEL = OUT / "naive_bayes_full_field_model.json"
TOKEN = re.compile(r"[a-z0-9]+")
ALPHA = 1.0


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def main() -> None:
    gold = pd.read_csv(GOLD, dtype=str).fillna("")
    train = gold.loc[gold.evaluation_split.eq("development")].copy()
    if len(train) < 200 or gold.evaluation_split.eq("held_out").sum() < 50:
        raise ValueError("Expected development and held-out all-field partitions are missing.")
    vocab_counts = Counter(token for text in train.text for token in tokens(text))
    vocab = {token for token, count in vocab_counts.items() if count >= 2}
    fitted: dict[str, dict] = {}
    for field in CODE_FIELDS:
        labels = sorted(train[field].unique())
        docs = Counter(train[field])
        word_counts = {label: Counter() for label in labels}
        totals = Counter()
        for _, row in train.iterrows():
            label = row[field]
            selected = [token for token in tokens(row.text) if token in vocab]
            word_counts[label].update(selected)
            totals[label] += len(selected)
        fitted[field] = {
            "labels": labels, "document_counts": dict(docs), "token_totals": dict(totals),
            "word_counts": {label: dict(counts) for label, counts in word_counts.items()},
        }
    def predict(field: str, text: str) -> str:
        model = fitted[field]
        selected = [token for token in tokens(text) if token in vocab]
        labels = model["labels"]
        scores = {}
        for label in labels:
            score = math.log((model["document_counts"][label] + ALPHA) / (len(train) + ALPHA * len(labels)))
            denom = model["token_totals"][label] + ALPHA * len(vocab)
            counts = model["word_counts"][label]
            score += sum(math.log((counts.get(token, 0) + ALPHA) / denom) for token in selected)
            scores[label] = score
        return max(labels, key=lambda label: (scores[label], label))
    predictions = gold[["item_id"]].copy()
    for field in CODE_FIELDS:
        predictions[field] = [predict(field, text) for text in gold.text]
    predictions["model_name"] = "naive_bayes_full_field_v1"
    predictions["training_partition"] = "development_only"
    OUT.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(PREDICTIONS, index=False)
    model_card = {
        "model_name": "naive_bayes_full_field_v1", "algorithm": "multinomial naive Bayes", "alpha": ALPHA,
        "tokenizer": TOKEN.pattern, "vocabulary_size": len(vocab), "training_rows": len(train),
        "held_out_rows_not_used_for_training": int(gold.evaluation_split.eq("held_out").sum()),
        "label_fields": CODE_FIELDS,
        "training_data_sha256": hashlib.sha256(train[["item_id", "text", *CODE_FIELDS]].to_csv(index=False).encode()).hexdigest(),
        "limitations": "Conventional bag-of-words baseline; factual calibration requires release-time source checking and should not be automated without retained evidence.",
        "field_models": fitted,
    }
    MODEL.write_text(json.dumps(model_card, indent=2), encoding="utf-8")
    print(json.dumps({key: model_card[key] for key in ("model_name", "training_rows", "held_out_rows_not_used_for_training", "vocabulary_size")}, indent=2))


if __name__ == "__main__":
    main()
