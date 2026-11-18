"""Camera-ready copy of rapidbench/scripts/make_figures.py (v1.6): identical except the two
in-figure titles are removed, Fig. 1 uses a greyscale-safe scale, and paths are arguments. Usage: python3 -I make_figures_cr.py <results_dir> <out_dir> [height_fig1_in] [height_fig2_in]
Without the title the plotting area grows; passing a height reduced by the title height keeps the plotting area as in the submitted figure."""
"""Paper figures from results/grid_synthetic.csv (real 180-cell grid).
Fig 1: detection rate heatmap, class x severity, mean over 5 seeds.
Fig 2: max RDM by class at p=0.05 vs the 1% materiality line, silent
classes flagged. IEEE single-column sizing. Writes figs/*.png/.pdf."""
import sys
RES, OUT = sys.argv[1], sys.argv[2]
H1 = float(sys.argv[3]) if len(sys.argv) > 3 else 3.1   # original height 3.1 in
H2 = float(sys.argv[4]) if len(sys.argv) > 4 else 2.6   # original height 2.6 in
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"font.size": 8, "font.family": "serif",
                     "axes.linewidth": 0.6,
                     "pdf.fonttype": 42, "ps.fonttype": 42})
Path(OUT).mkdir(exist_ok=True)
g = pd.read_csv(RES + "/grid_synthetic.csv")
g["cls"] = g["injector"].str.split("_").str[0]
order = sorted(g["cls"].unique())
sevs = sorted(g["severity"].unique())

# Fig 1: detection heatmap
piv = (g.groupby(["cls", "severity"])["detected_any"].mean()
         .unstack()[sevs].loc[order])
fig, ax = plt.subplots(figsize=(3.5, H1))
# camera-ready: greyscale-safe scale (white = never detected, dark = always detected),
# the same convention as Fig. 3; the submitted figure used the red-green RdYlGn map
from matplotlib.colors import LinearSegmentedColormap
GREY = LinearSegmentedColormap.from_list("grey_cr", ["#ffffff", "#3a3a3a"])
im = ax.imshow(piv.values, cmap=GREY, vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(sevs)), [f"{s:g}" for s in sevs])
ax.set_yticks(range(len(order)), order)
ax.set_xlabel("Injection severity $p$")
for i in range(len(order)):
    for j in range(len(sevs)):
        val = piv.values[i, j]
        ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7,
                color="white" if val >= 0.5 else "black")
# camera-ready: title removed (titles live in the captions)
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
fig.tight_layout()
b = ax.get_position(); print("fig1 axes height in:", round(b.height * H1, 3), "width in:", round(b.width * 3.5, 3))
for ext in ("png", "pdf"):
    fig.savefig(OUT + f"/fig_detection_heatmap.{ext}", dpi=300)
plt.close(fig)

# Fig 2: materiality vs detection at p=0.05
m = g[g["severity"] == 0.05].groupby("cls").agg(
    max_rdm=("max_rdm", "mean"), det=("detected_any", "mean")).loc[order]
fig, ax = plt.subplots(figsize=(3.5, H2))
colors = ["#2b8a3e" if d == 1 else ("#e67700" if d > 0 else "#c92a2a")
          for d in m["det"]]
bars = ax.bar(range(len(m)), np.maximum(100 * m["max_rdm"], 1e-3),
              color=colors, width=0.7)
for i, d in enumerate(m["det"]):
    if d == 0:
        bars[i].set_hatch("///")
        bars[i].set_edgecolor("black")
ax.axhline(1.0, color="black", ls="--", lw=0.8)
ax.text(3.0, 1.3, "1% materiality", ha="center", fontsize=7)
ax.set_yscale("log")
ax.set_ylabel("Mean max RDM across $S_1$-$S_6$ (%)")
ax.set_xticks(range(len(m)), m.index, rotation=90)
# camera-ready: title removed (titles live in the captions)
fig.tight_layout()
b = ax.get_position(); print("fig2 axes height in:", round(b.height * H2, 3), "width in:", round(b.width * 3.5, 3))
for ext in ("png", "pdf"):
    fig.savefig(OUT + f"/fig_rdm_by_class.{ext}", dpi=300)
plt.close(fig)

sil = m[(m["det"] == 0) & (100 * m["max_rdm"] > 1)]
print("figs written; never-detected & material at p=0.05:",
      ", ".join(f"{c} ({100*r:.1f}%)" for c, r in
                zip(sil.index, sil["max_rdm"])))
