"""Render dependency-free SVG figures directly from the dashboard payload."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/report/figures"
OUT.mkdir(parents=True, exist_ok=True)
data = json.loads((ROOT / "dashboard/data/monitoring_payload.json").read_text())

W, H = 1050, 520
M = {"l": 70, "r": 28, "t": 58, "b": 78}
COLORS = {"actual": "#12355b", "prediction": "#d9702b", "gap": "#b23a48", "green": "#2f7f66", "grid": "#dbe4ee"}

def date(value):
    return datetime.fromisoformat(value[:10]).timestamp()

def esc(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def line_path(rows, x, y, key):
    return " ".join(("M" if i == 0 else "L") + f" {x(date(row['month'])):.1f} {y(row[key]):.1f}" for i, row in enumerate(rows) if row.get(key) is not None)

def chart(title, rows, series, filename, y_label, note, y_range=None, band=None, zero=False, x_labels=None):
    values = [float(row[key]) for key, *_ in series for row in rows if row.get(key) is not None]
    if band:
        values += [float(row[band[0]]) for row in rows] + [float(row[band[1]]) for row in rows]
    low, high = y_range if y_range else (min(values), max(values))
    if not y_range:
        padding = (high - low) * .10 or 1
        low, high = low - padding, high + padding
    xmin, xmax = date(rows[0]["month"]), date(rows[-1]["month"])
    x = lambda value: M["l"] + (value - xmin) / (xmax - xmin or 1) * (W - M["l"] - M["r"])
    y = lambda value: H - M["b"] - (float(value) - low) / (high - low) * (H - M["t"] - M["b"])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">', '<style>text{font-family:Arial,sans-serif;fill:#263648}.title{font-size:22px;font-weight:700}.label{font-size:13px;fill:#526477}.legend{font-size:13px}.note{font-size:12px;fill:#526477}</style>', '<rect width="100%" height="100%" fill="white"/>', f'<text x="{M["l"]}" y="31" class="title">{esc(title)}</text>']
    for index in range(5):
        value = high - index * (high - low) / 4
        yy = y(value)
        parts += [f'<line x1="{M["l"]}" x2="{W-M["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{COLORS["grid"]}"/>', f'<text x="{M["l"]-9}" y="{yy+4:.1f}" text-anchor="end" class="label">{value:.0f}</text>']
    if zero and low < 0 < high:
        parts.append(f'<line x1="{M["l"]}" x2="{W-M["r"]}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="#334155" stroke-width="1.2"/>')
    if band:
        upper = " ".join(f"{x(date(row['month'])):.1f},{y(row[band[1]]):.1f}" for row in rows)
        lower = " ".join(f"{x(date(row['month'])):.1f},{y(row[band[0]]):.1f}" for row in reversed(rows))
        parts.append(f'<polygon points="{upper} {lower}" fill="{COLORS["prediction"]}" fill-opacity=".16"/>')
    for index, (key, label, color) in enumerate(series):
        parts.append(f'<path d="{line_path(rows, x, y, key)}" fill="none" stroke="{color}" stroke-width="2.8"/>')
        legend_x = M["l"] + index * 210
        parts += [f'<line x1="{legend_x}" x2="{legend_x+22}" y1="{M["t"]-18}" y2="{M["t"]-18}" stroke="{color}" stroke-width="3"/>', f'<text x="{legend_x+28}" y="{M["t"]-13}" class="legend">{esc(label)}</text>']
    labels = x_labels or [(rows[0]["month"], rows[0]["month"][:4]), (rows[len(rows)//2]["month"], rows[len(rows)//2]["month"][:4]), (rows[-1]["month"], rows[-1]["month"][:4])]
    for raw, label in labels:
        parts.append(f'<text x="{x(date(raw)):.1f}" y="{H-M["b"]+28}" text-anchor="middle" class="label">{esc(label)}</text>')
    parts += [f'<text x="{M["l"]}" y="{H-18}" class="note">{esc(note)}</text>', f'<text x="20" y="{H/2}" transform="rotate(-90 20 {H/2})" class="label">{esc(y_label)}</text>', '</svg>']
    (OUT / filename).write_text("\n".join(parts))

forecast = data["forecast"]
chart("Consumer sentiment and economic-only prediction", forecast, [("sentiment", "Michigan sentiment", COLORS["actual"]), ("prediction", "Economic-only prediction", COLORS["prediction"])], "figure_1_sentiment_forecast.svg", "Index points", "Source: dashboard payload. Shaded region is the 95% prediction interval.", band=("prediction_lower_95", "prediction_upper_95"))
chart("Sentiment gap: observed minus economic-only prediction", forecast, [("sentiment_gap", "Sentiment gap", COLORS["gap"])], "figure_2_sentiment_gap.svg", "Index points", "Negative values are unexplained pessimism under this model, not proof of media bias.", zero=True)
media = data["media"]
media_percent = [dict(row, **{key: row[key] * 100 for key in ("tone_negative_share", "price_level_frame_share", "frame_household_experience_share", "factual_calibrated_share")}) for row in media]
chart("Validated media measures in the dashboard corpus", media_percent, [("tone_negative_share", "Negative tone", COLORS["gap"]), ("price_level_frame_share", "Price-level frame", COLORS["prediction"]), ("frame_household_experience_share", "Household frame", COLORS["green"]), ("factual_calibrated_share", "Factually calibrated", COLORS["actual"])], "figure_3_validated_media_measures.svg", "Share of adjudicated items (%)", "Source: dashboard payload. October is partial-period and represents content supply, not exposure.", y_range=(0, 105), x_labels=[(row["month"], datetime.fromisoformat(row["month"][:10]).strftime("%b %Y")) for row in media])
print(OUT)
