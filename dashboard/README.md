# Monitoring dashboard

The dashboard is a buildless local website. It reads `data/monitoring_payload.json`, produced by `src/pipeline.py`.

```bash
python ../src/pipeline.py
python -m http.server 8000
```

Then visit `http://localhost:8000`. A local web server is required because browsers block `fetch()` from a file URL.

The pipeline updates the dashboard payload automatically. The dashboard never fills missing media measures with zeros. The current `data/media_monthly.csv` is a 312-item, source-blinded, all-field validated aggregate; it remains descriptive rather than evidence of exposure or causation. In a genuine pre-election update, replace the availability assumptions in `src/pipeline.py` with release timestamps and vintage values, freeze model versions, and record each update date.
