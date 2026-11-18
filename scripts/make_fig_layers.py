"""Figure: which detection layer sees which fault class (severity 0.05, S-A).

Columns: V1 rules, V1b GX suite, V2 drift, then the five V3 reviewers.
Cell states: filled = detected / mechanism identified; hatched = flagged
without identifying the injected mechanism; empty = silent.
Sources: results/grid_synthetic.csv, results/gx_matrix.csv,
results/e3_adjudicated.csv.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd

plt.rcParams.update({"font.size": 8, "font.family": "serif",
                     "pdf.fonttype": 42, "ps.fonttype": 42})

FAULTS = [f"F{i:02d}" for i in range(1, 13)]
LABELS = ["F01 HS zero loss", "F02 unit mismatch", "F03 stale FX",
          "F04 CIF/FOB", "F05 tariff vintage", "F06 outcome leak",
          "F07 dup.\\ amendments".replace("\\ ", " "), "F08 zero-fill",
          "F09 partner swap", "F10 schema fallback", "F11 dedup overreach",
          "F12 code drift"]

g = pd.read_csv("results/grid_synthetic.csv")
g05 = g[g.severity == 0.05].copy()
g05["F"] = g05.injector.str[:3]
v1 = g05.groupby("F").rules_fired.mean()
v2 = g05.groupby("F").drift_fired.mean()

gx = pd.read_csv("results/gx_matrix.csv")
gx["F"] = gx.injector.str[:3]
v1b = gx.set_index("F").any_fired

e3 = pd.read_csv("results/e3_adjudicated.csv")
e3 = e3[e3.fault != "F00_clean"].copy()
e3["F"] = e3.fault.str[:3]
MODELS = [("anthropic/claude-sonnet-4.5", "Claude"),
          ("google/gemini-2.5-pro", "Gemini"),
          ("meta-llama/llama-3.3-70b-instruct", "Llama"),
          ("openai/gpt-4o", "GPT-4o"),
          ("deepseek/deepseek-chat", "DeepSeek")]

cols = ["Rules", "GX", "Drift"] + [m[1] for m in MODELS]
fig, ax = plt.subplots(figsize=(3.5, 2.9))

def cell(x, y, state):
    if state == "full":
        ax.add_patch(Rectangle((x, y), 0.86, 0.86, facecolor="#2b2b2b",
                               edgecolor="none"))
    elif state == "flag":
        ax.add_patch(Rectangle((x, y), 0.86, 0.86, facecolor="#ffffff",
                               edgecolor="#2b2b2b", hatch="////", lw=0.5))
    else:
        ax.add_patch(Rectangle((x, y), 0.86, 0.86, facecolor="#ffffff",
                               edgecolor="#c9c9c9", lw=0.5))

for i, F in enumerate(FAULTS):
    y = len(FAULTS) - 1 - i
    cell(0, y, "full" if v1.get(F, 0) >= 0.5 else "none")
    cell(1, y, "full" if bool(v1b.get(F, False)) else "none")
    dv = v2.get(F, 0)
    cell(2, y, "full" if dv >= 0.5 else "none")
    if 0 < dv < 1:
        ax.text(2.43, y + 0.43, f"{dv:.1f}", ha="center", va="center",
                fontsize=5.5, color="#ffffff" if dv >= 0.5 else "#2b2b2b")
    for j, (mid, _) in enumerate(MODELS):
        r = e3[(e3.model == mid) & (e3.F == F)].iloc[0]
        st = "full" if r.identified else ("flag" if r.flagged else "none")
        cell(3.2 + j, y, st)

for j, c in enumerate(cols):
    x = j if j < 3 else 3.2 + (j - 3)
    ax.text(x + 0.43, len(FAULTS) + 0.15, c, ha="center", va="bottom",
            fontsize=7, rotation=45)
for i, lab in enumerate(LABELS):
    ax.text(-0.15, len(FAULTS) - 1 - i + 0.43, lab, ha="right",
            va="center", fontsize=6.5)

ax.text(1.43, -0.75, "automated", ha="center", fontsize=6.5, style="italic")
ax.text(5.6, -0.75, "LLM reviewers (V3)", ha="center", fontsize=6.5,
        style="italic")
ax.plot([-0.05, 2.91], [-0.45, -0.45], lw=0.5, color="#666")
ax.plot([3.25, 8.01], [-0.45, -0.45], lw=0.5, color="#666")

ax.set_xlim(-2.6, 8.3)
ax.set_ylim(-1.1, len(FAULTS) + 1.2)
ax.set_aspect("equal")
ax.axis("off")
fig.tight_layout(pad=0.1)
fig.savefig("figs/fig_layers.pdf", bbox_inches="tight")
fig.savefig("figs/fig_layers.png", dpi=300, bbox_inches="tight")
print("wrote figs/fig_layers.{pdf,png}")
