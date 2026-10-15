"""Validate paired human all-field labels and report agreement by field/class/source."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from build_full_field_validation_packets import CODE_FIELDS, INTERNAL, KEY, OUT


VALID = {
    "tone": {"negative", "neutral", "mixed", "positive"},
    "factual_calibration": {"calibrated", "materially incomplete-or-misleading", "unverifiable"},
    "political_valence": {"credit", "blame", "neutral", "none"},
}


def read(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, dtype=str, encoding=encoding).fillna("")
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {path}")


def kappa(left: pd.Series, right: pd.Series) -> float | None:
    if not len(left): return None
    labels = set(left) | set(right)
    observed = (left == right).mean()
    expected = sum((left == label).mean() * (right == label).mean() for label in labels)
    return None if expected == 1 else round(float((observed - expected) / (1 - expected)), 3)


def main() -> None:
    key = read(KEY)
    expected = set(key.blind_id)
    a, b = read(OUT / "annotator_a.csv"), read(OUT / "annotator_b.csv")
    records, validity = {}, {}
    for label, frame in (("a", a), ("b", b)):
        frame = frame.loc[frame.blind_id.isin(expected) & frame.label_provenance.eq("human_independent")].copy()
        invalid = 0
        for field in CODE_FIELDS:
            allowed = VALID.get(field, {"0", "1"} if field.startswith(("salience_", "frame_")) else None)
            if allowed is not None:
                invalid += int((frame[field].ne("") & ~frame[field].isin(allowed)).sum())
        invalid += int(((frame.political_attribution_target.eq("none")) != (frame.political_valence.eq("none"))).sum())
        required_complete = frame[CODE_FIELDS].ne("").all(axis=1)
        factual_evidence = frame.factual_calibration.eq("unverifiable") | (frame.benchmark_reference.ne("") & frame.evidence_excerpt.ne(""))
        records[label] = frame.loc[required_complete & factual_evidence].drop_duplicates("blind_id", keep="first")
        validity[label] = {"completed": int(len(records[label])), "invalid_values": invalid, "missing_factual_evidence": int((~factual_evidence & required_complete).sum())}
    paired = records["a"][["blind_id", *CODE_FIELDS]].merge(records["b"][["blind_id", *CODE_FIELDS]], on="blind_id", suffixes=("_a", "_b"))
    paired = paired.merge(key[["blind_id", "source_stratum", "evaluation_split"]], on="blind_id", how="left")
    INTERNAL.mkdir(parents=True, exist_ok=True)
    paired.to_csv(INTERNAL / "paired_full_field_labels.csv", index=False)
    field_rows, detail_rows = [], []
    for field in CODE_FIELDS:
        left, right = paired[f"{field}_a"], paired[f"{field}_b"]
        field_rows.append({"field": field, "paired": int(len(paired)), "agreement": None if not len(paired) else round(float((left == right).mean()), 3), "cohen_kappa": kappa(left, right)})
        for stratum, group in paired.groupby("source_stratum", dropna=False):
            for label in sorted(set(group[f"{field}_a"]) | set(group[f"{field}_b"])):
                support = int((group[f"{field}_a"] == label).sum())
                matches = int(((group[f"{field}_a"] == label) & (group[f"{field}_b"] == label)).sum())
                detail_rows.append({"field": field, "class": label, "source_stratum": stratum or "missing", "support_a": support, "agreement_count": matches, "agreement_rate_within_a_class": None if not support else round(matches / support, 3)})
    validation = Path(__file__).resolve().parents[1] / "data/corpus/validation"
    validation.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(field_rows, columns=["field", "paired", "agreement", "cohen_kappa"]).to_csv(validation / "full_field_human_agreement_by_field.csv", index=False)
    pd.DataFrame(detail_rows, columns=["field", "class", "source_stratum", "support_a", "agreement_count", "agreement_rate_within_a_class"]).to_csv(validation / "full_field_human_agreement_by_class_source.csv", index=False)
    complete = len(paired) == len(expected) >= 300 and all(not validity[x]["invalid_values"] and not validity[x]["missing_factual_evidence"] for x in validity)
    summary = {"required_pairs": 300, "expected_blinded_items": len(expected), "paired_complete_all_fields": int(len(paired)), "by_annotator": validity, "gate_passed": complete, "message": "All-field independent-label gate passed; adjudicate disagreements." if complete else "Blocked: each blinded item needs two complete, valid all-field labels and factual evidence where applicable."}
    (validation / "full_field_label_validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
