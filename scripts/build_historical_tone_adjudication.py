"""Build a blind historical tone-adjudication queue and finalized label table."""
from __future__ import annotations
import csv, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "data/corpus/historical/independent_validation"
KEY = ROOT / "data/corpus/historical/validation_internal/historical_validation_blind_key.csv"
OUT = PACKETS / "adjudication"; DECISIONS = OUT / "historical_tone_decisions.csv"

def read(path):
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            with path.open(encoding=encoding, newline="") as stream:
                return list(csv.DictReader(stream))
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 0, f"Cannot decode {path}")
def clean(x): return (x or "").strip()
def main():
    OUT.mkdir(parents=True, exist_ok=True); now = datetime.now(ZoneInfo("America/New_York")).replace(microsecond=0).isoformat()
    a = {r["blind_id"]:r for r in read(PACKETS / "annotator_a.csv") if clean(r.get("label_provenance")) == "human_independent" and clean(r.get("tone"))}
    b = {r["blind_id"]:r for r in read(PACKETS / "annotator_b.csv") if clean(r.get("label_provenance")) == "human_independent" and clean(r.get("tone"))}
    key = {r["blind_id"]:r["item_id"] for r in read(KEY)}; prior = {r["blind_id"]:r for r in read(DECISIONS)} if DECISIONS.exists() else {}
    final=[]; queue=[]; decisions=[]
    for blind_id in sorted(set(a)&set(b)):
        left,right=a[blind_id],b[blind_id]; differs=clean(left["tone"]) != clean(right["tone"]); old=prior.get(blind_id,{})
        resolved=(not differs) or bool(clean(old.get("adjudicated_tone")) and clean(old.get("adjudicator")))
        row={"blind_id":blind_id,"item_id":key[blind_id],"text":clean(left["text"]),"text_representation":clean(left.get("text_representation")),"tone_a":clean(left["tone"]),"tone_b":clean(right["tone"]),"adjudicated_tone":clean(left["tone"]) if not differs else (clean(old.get("adjudicated_tone")) if resolved else ""),"adjudication_status":"historical_independent_consensus" if not differs else ("historical_manual_adjudication" if resolved else "needs_historical_tone_adjudication"),"adjudicator":"consensus_rule_v1" if not differs else clean(old.get("adjudicator")),"adjudication_date":now if not differs else clean(old.get("adjudication_date")),"adjudication_rationale":"independent annotators agreed" if not differs else clean(old.get("adjudication_rationale"))}
        final.append(row)
        if differs:
            decisions.append({k:row[k] for k in ("blind_id","text_representation","text","tone_a","tone_b","adjudicated_tone","adjudicator","adjudication_date","adjudication_rationale")})
            if not resolved: queue.append(row)
    for path, rows in ((DECISIONS,decisions),(OUT/"historical_tone_adjudications.csv",final),(OUT/"historical_tone_adjudication_queue.csv",queue)):
        fields=list(rows[0]) if rows else (["blind_id","text_representation","text","tone_a","tone_b","adjudicated_tone","adjudicator","adjudication_date","adjudication_rationale"] if path==DECISIONS else list(final[0]) if final else [])
        with path.open("w",encoding="utf-8",newline="") as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    summary={"paired":len(final),"consensus":sum(r["adjudication_status"]=="historical_independent_consensus" for r in final),"unresolved":len(queue),"ready":not queue}
    (OUT/"historical_tone_adjudication_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8"); print(json.dumps(summary,indent=2))

if __name__ == "__main__": main()
