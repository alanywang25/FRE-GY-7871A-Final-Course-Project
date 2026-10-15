"""Normalize top-level Markdown section numbers in the analysis notebook."""
import json
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "notebooks/perceptual_bias_analysis.ipynb"
notebook = json.loads(path.read_text())

headings = {
    "## 1. Data provenance, timing, and limits": "## 1. Data provenance, timing, and limits",
    "## 2. Prespecified economic-only model": "## 2. Prespecified economic-only model",
    "## 3. Autocorrelation and genuine month-end vintages": "## 3. Autocorrelation and genuine month-end vintages",
    "## 4. Supplementary extension: household-stress proxies": "## 4. Supplementary extension: household-stress proxies",
    "## 5. Expanded public controls and real-time guardrail": "## 5. Expanded public controls and real-time guardrail",
    "## 6. Media measurement, source comparison, and model gate": "## 6. Media measurement, source comparison, and model gate",
    "## 6. Observational association and causal-design boundary": "## 7. Observational association and causal-design boundary",
    "## 8. Historical media comparison, third model, and subgroup contracts": "## 8. Historical media comparison, third model, and subgroup contracts",
    "## 5. Causal design and falsification checks": "## 9. Causal design and falsification checks",
    "## 6. Produce reproducible dashboard inputs": "## 10. Produce reproducible dashboard inputs",
    "## Interpretation": "## 11. Interpretation",
}

seen = set()
for cell in notebook["cells"]:
    if cell.get("cell_type") != "markdown":
        continue
    source = "".join(cell.get("source", []))
    first_line, *rest = source.splitlines(keepends=True)
    if first_line.rstrip("\n") in headings:
        replacement = headings[first_line.rstrip("\n")]
        cell["source"] = [replacement + ("\n" if first_line.endswith("\n") else ""), *rest]
        seen.add(first_line.rstrip("\n"))

missing = set(headings) - seen
if missing:
    raise RuntimeError(f"Notebook headings not found: {sorted(missing)}")

path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
print(path)
