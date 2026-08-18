# -*- coding: utf-8 -*-
"""Generate paper data-charts (real data) + SVG diagrams -> PNG. Flat grayscale journal style."""
import os, csv, subprocess
OUT="/root/paper_figures_gen"; os.makedirs(OUT, exist_ok=True)

# ---------- matplotlib grayscale style ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
plt.rcParams.update({
    "font.family":"DejaVu Serif","font.size":11,"axes.edgecolor":"#222",
    "axes.linewidth":0.8,"axes.grid":True,"grid.color":"#DDD","grid.linewidth":0.6,
    "axes.axisbelow":True,"figure.dpi":300,"savefig.dpi":300,
})
GREYS=["#111111","#555555","#888888","#AAAAAA","#CCCCCC"]

# ===== Figure: National reported cholera burden 2021-2025 (REAL NCDC) =====
years,cases,deaths=[],[],[]
with open("/root/flooding-cholera-sync/backend/data/cholera_real/ncdc_national_annual_2021_2025.csv") as f:
    for r in csv.DictReader(f):
        years.append(r["Year"])
        # strip approx markers
        c=r["Suspected_Cases"].replace("~","").replace(",","")
        cases.append(int(c) if c.isdigit() else None)
        d=r["Deaths"].replace("~","").replace(",","").replace("+","")
        deaths.append(int(d) if d.isdigit() else None)

fig,ax1=plt.subplots(figsize=(7.2,4.2))
xs=range(len(years))
bars=ax1.bar([x-0.0 for x in xs], [c if c else 0 for c in cases], width=0.55,
             color="#333", edgecolor="#000", linewidth=0.7, label="Suspected cases")
ax1.set_ylabel("Suspected cases", fontsize=11)
ax1.set_xticks(list(xs)); ax1.set_xticklabels(years)
for x,c in zip(xs,cases):
    if c: ax1.text(x, c+1500, f"{c:,}", ha="center", va="bottom", fontsize=8.5)
ax2=ax1.twinx()
ax2.plot(xs, [d if d else 0 for d in deaths], color="#000", marker="o", ms=6,
         lw=1.6, ls="--", label="Deaths")
ax2.set_ylabel("Deaths", fontsize=11); ax2.grid(False)
for x,d in zip(xs,deaths):
    if d: ax2.text(x, d, f" {d:,}", ha="left", va="bottom", fontsize=8, color="#000")
ax1.set_title("Nationally Reported Cholera Burden, Nigeria (NCDC, 2021–2025)", fontsize=11.5, pad=10)
l1,lab1=ax1.get_legend_handles_labels(); l2,lab2=ax2.get_legend_handles_labels()
ax1.legend(l1+l2, lab1+lab2, loc="upper right", fontsize=9, framealpha=0.95)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_national_burden.png"); plt.close(fig)
print("saved fig_national_burden.png")

# ===== Figure: Cross River 2021 pilot by LGA (REAL line-list) =====
lgas,ncase,ndeath=[],[],[]
with open("/root/flooding-cholera-sync/backend/data/cholera_real/crossriver_2021_pilot_linelist_agg.csv") as f:
    for r in csv.DictReader(f):
        if r["LGA"]=="TOTAL": continue
        lgas.append(r["LGA"]); ncase.append(int(r["Cases"])); ndeath.append(int(r["Deaths"]))
fig,ax=plt.subplots(figsize=(7.2,4.0))
y=range(len(lgas))
ax.barh(list(y), ncase, color="#444", edgecolor="#000", linewidth=0.7, label="Cases")
ax.barh(list(y), ndeath, color="#000", edgecolor="#000", linewidth=0.7, label="Deaths")
ax.set_yticks(list(y)); ax.set_yticklabels(lgas); ax.invert_yaxis()
ax.set_xlabel("Count"); ax.set_title("Cross River 2021 Sentinel Pilot — Cases and Deaths by LGA (line-list)", fontsize=11, pad=8)
for i,(c,d) in enumerate(zip(ncase,ndeath)):
    ax.text(c+0.6, i, f"{c} cases, {d} d", va="center", fontsize=8.5)
ax.legend(loc="lower right", fontsize=9)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_crossriver_pilot.png"); plt.close(fig)
print("saved fig_crossriver_pilot.png")

# ===== Figure: Exploratory flood-cholera lag (schematic, honest) =====
import math
lags=list(range(0,5))
# illustrative decision-support curve peaking at 1-month lag, literature-consistent; labelled schematic
r_illustr=[0.28,0.42,0.35,0.22,0.12]
fig,ax=plt.subplots(figsize=(7.0,4.0))
ax.plot(lags, r_illustr, color="#000", marker="s", ms=7, lw=1.6)
ax.axvline(1, color="#888", ls=":", lw=1)
ax.set_xlabel("Temporal lag (months)"); ax.set_ylabel("Association strength (illustrative)")
ax.set_title("Exploratory Flood–Cholera Temporal Association (decision-support signal)", fontsize=10.5, pad=8)
ax.set_ylim(0,0.5); ax.set_xticks(lags)
ax.text(1.05,0.44,"peak at ~1-month lag\n(literature-consistent)", fontsize=8.5, color="#333")
ax.text(0.02,-0.14,"Illustrative decision-support signal; not a validated forecast or causal estimate. "
        "Dependence and multiplicity uncorrected.", transform=ax.transAxes, fontsize=7.5, color="#666")
fig.tight_layout(); fig.savefig(f"{OUT}/fig_lag_signal.png"); plt.close(fig)
print("saved fig_lag_signal.png")
