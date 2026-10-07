"""Build the NEW Figure 13 (schema-detection benchmark) from the real NIM run.
Monochrome / flat minimal styling. Reads benchmark_trials.jsonl only."""
import json, sys
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

TRIALS = sys.argv[1] if len(sys.argv) > 1 else "/home/claude-agent/task_b/benchmark_trials.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/root/cholera_hod_tasks/fig13_copilot_bench_v10.png"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8, "axes.grid": True, "grid.color": "#DDDDDD", "grid.linewidth": 0.6, "figure.dpi": 400})

rows = [json.loads(l) for l in open(TRIALS) if l.strip()]
assert len(rows) == 72, len(rows)

def rate(rs, key):
    v = [r[key] for r in rs if r.get(key) is not None]
    return 100.0 * sum(bool(x) for x in v) / len(v) if v else np.nan

metrics = [("grounding", "Schema grounding\n(no invented columns)"), ("correct_lga_binding", "LGA field\ncorrectly bound"),
           ("correct_case_binding", "Case-count field\ncorrectly bound"), ("correct_deaths_binding", "Death-count field\ncorrectly bound")]
U = [r for r in rows if r["condition"] == "unconstrained"]
G = [r for r in rows if r["condition"] == "schema-grounded"]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), gridspec_kw={"width_ratios": [1.05, 1.25]})
ax = axes[0]; x = np.arange(len(metrics)); w = 0.36
va = [rate(U, m[0]) for m in metrics]; vg = [rate(G, m[0]) for m in metrics]
b1 = ax.bar(x - w/2, va, w, label=f"Unconstrained prompt (n={len(U)})", color="#BBBBBB", edgecolor="#222222", linewidth=0.8)
b2 = ax.bar(x + w/2, vg, w, label=f"Schema-grounded prompt (n={len(G)})", color="#444444", edgecolor="#111111", linewidth=0.8)
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 2, f"{b.get_height():.1f}", ha="center", va="bottom", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([m[1] for m in metrics], fontsize=8)
ax.set_ylabel("Trials passing (%)"); ax.set_ylim(0, 118)
ax.set_title("(a) Effect of tool-grounding on schema detection", fontsize=10, pad=8)
ax.legend(frameon=False, fontsize=8, loc="lower left"); ax.set_axisbelow(True)

CLASS = {"canonical": "canonical", "canonical_b": "canonical", "abbreviated_ncdc": "abbreviated", "abbreviated_ncdc_b": "abbreviated",
         "dirty_header": "dirty", "dirty_header_b": "dirty", "decoy_schema": "decoys", "decoy_schema_b": "decoys",
         "wide_table": "wide", "opaque_coded": "opaque", "opaque_coded_b": "opaque", "reduced_schema": "missing_fields"}
order = ["canonical", "abbreviated", "dirty", "decoys", "wide", "opaque", "missing_fields"]
labels = ["Canonical", "Abbreviated", "Dirty\nheaders", "Decoy\ncolumns", "Wide\ntable", "Opaque\ncodes", "Missing\nfields"]
ax = axes[1]
ga = [rate([r for r in U if CLASS[r["variant"]] == d], "grounding") for d in order]
gg = [rate([r for r in G if CLASS[r["variant"]] == d], "grounding") for d in order]
x = np.arange(len(order))
ax.bar(x - w/2, ga, w, color="#BBBBBB", edgecolor="#222222", linewidth=0.8)
ax.bar(x + w/2, gg, w, color="#444444", edgecolor="#111111", linewidth=0.8)
for i, (a, g) in enumerate(zip(ga, gg)):
    ax.text(i - w/2, a + 2, f"{a:.0f}", ha="center", fontsize=7.5); ax.text(i + w/2, g + 2, f"{g:.0f}", ha="center", fontsize=7.5)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=7.5)
ax.set_ylabel("Schema grounding (%)"); ax.set_ylim(0, 118)
ax.set_title("(b) Grounding rate by schema difficulty class", fontsize=10, pad=8); ax.set_axisbelow(True)
plt.tight_layout(); plt.savefig(OUT, bbox_inches="tight"); print("wrote", OUT)
print("panel a  U:", [f"{v:.1f}" for v in va], " G:", [f"{v:.1f}" for v in vg])
print("panel b  U:", [f"{v:.0f}" for v in ga], " G:", [f"{v:.0f}" for v in gg])
