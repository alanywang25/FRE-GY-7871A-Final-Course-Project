# Consensus adjudication output

`adjudicated_item_labels.csv` retains both annotator values and writes an adjudicated value only when the two reviewed packets agree across all coding fields. Disagreements are deliberately left blank in the adjudicated fields and appear in `adjudication_queue.csv` for a named human adjudicator.

Enter final decisions in `manual_adjudication_decisions.csv`; provide a named adjudicator and values for every disputed field. Re-run `scripts/build_adjudicated_media_data.py` to merge those decisions while preserving the original annotator values and rationale.

`data/media_monthly.csv` aggregates only consensus records that pass the corpus default inclusion rule and are neither duplicates nor suspected automated posts. Its `available_on` timestamp is the time the consensus build ran, not the original publication time. The aggregate is therefore a **provisional consensus measure**, not an independent-human reliability-validated measure and not suitable for historical real-time forecasting.
