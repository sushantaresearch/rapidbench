"""Paper 65 camera-ready: recompute every number added in response to R4/R5 from the
frozen v1.6 results (no new runs). Usage:
    python3 -I analysis65.py <rapidbench_repo_dir> <out.json>
Silent = material (max RDM > t) and not detected. Raw detection = any V1 rule fired or V2 drift fired.
Net detection = the same, ignoring rules that fire on the substrate's own clean control
(controls_real.csv for S-B/S-C; controls_fpr.csv for S-A, where no rule fires on clean data).
"""
import json, sys
import pandas as pd
from scipy.stats import beta

R = sys.argv[1] + "/results/"
OUT = sys.argv[2]

def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return [round(100 * lo, 1), round(100 * hi, 1)]

ctl = pd.read_csv(R + "controls_real.csv")
cf = {r.substrate: (set(str(r.hits).split(";")) if r.fired else set())
      for _, r in ctl[ctl.tier == "V1_rules"].iterrows()}
fpr = pd.read_csv(R + "controls_fpr.csv")
cf["synthetic"] = set()
assert not fpr.V1_rules_fired.any() and not fpr.V2_drift_fired.any()

frames = {"S-A": pd.read_csv(R + "grid_synthetic.csv"),
          "S-B": pd.read_csv(R + "grid_date.csv"),
          "S-C": pd.read_csv(R + "grid_ctgan.csv")}
subname = {"S-A": "synthetic", "S-B": "date", "S-C": "ctgan"}

def hits(h):
    return [] if (pd.isna(h) or not str(h)) else [x for x in str(h).split(";") if x]

for s, g in frames.items():
    c = cf[subname[s]]
    g["cls"] = g.injector.str[:3]
    g["det_raw"] = g.rule_hits.apply(lambda h: len(hits(h)) > 0) | g.drift_fired
    g["det_net"] = g.rule_hits.apply(lambda h: len([x for x in hits(h) if x not in c]) > 0) | g.drift_fired
    # consistency with the shipped columns
    assert (g.det_raw == g.detected_any).all(), s
    assert ((~g.det_raw) & (g.max_rdm > 0.01) == g.silent).all(), s

netfile = pd.read_csv(R + "grid_date_net.csv")
assert int(netfile.silent_net.sum()) == int(((~frames["S-B"].det_net) & (frames["S-B"].max_rdm > 0.01)).sum())

out = {"clean_firing_rules": {k: sorted(v) for k, v in cf.items()}}
common = sorted(set.intersection(*[set(g.cls) for g in frames.values()]))
out["common_classes"] = common

def silent_counts(t):
    res = {}
    for s, g in frames.items():
        mat = g.max_rdm > t
        raw = int((mat & ~g.det_raw).sum()); net = int((mat & ~g.det_net).sum())
        by_cls = {k: int(v) for k, v in g[mat & ~g.det_net].groupby("cls").size().items()}
        gc = g[g.cls.isin(common)]
        res[s] = {"cells": len(g), "classes": int(g.cls.nunique()), "material": int(mat.sum()),
                  "silent_raw": raw, "silent_net": net,
                  "rate_net_pct": round(100 * net / len(g), 1), "ci_net": cp(net, len(g)),
                  "silent_net_by_class": by_cls,
                  "common_cells": len(gc),
                  "common_silent_net": int(((gc.max_rdm > t) & ~gc.det_net).sum()),
                  "common_silent_by_class": {k: int(v) for k, v in gc[(gc.max_rdm > t) & ~gc.det_net].groupby("cls").size().items()}}
    N = sum(v["cells"] for v in res.values())
    net = sum(v["silent_net"] for v in res.values()); raw = sum(v["silent_raw"] for v in res.values())
    cN = sum(v["common_cells"] for v in res.values()); cS = sum(v["common_silent_net"] for v in res.values())
    res["pooled"] = {"cells": N, "silent_net": net, "rate_net_pct": round(100 * net / N, 1), "ci_net": cp(net, N),
                     "silent_raw": raw, "rate_raw_pct": round(100 * raw / N, 1),
                     "common_cells": cN, "common_silent_net": cS, "common_rate_pct": round(100 * cS / cN, 1)}
    # classes silent (net) in every cell where material, by substrate
    return res

for t in (0.005, 0.01, 0.02):
    out[f"t={t}"] = silent_counts(t)

# per-class max RDM on each substrate (for the moderated claims)
out["max_rdm_pct"] = {s: {k: round(100 * v, 1) for k, v in g.groupby("cls").max_rdm.max().items()} for s, g in frames.items()}
# S-B: what raw detection rests on (cells whose only rule hit is the clean-firing R4 and no drift)
gB = frames["S-B"]
only_r4 = gB.rule_hits.apply(lambda h: hits(h) == ["R4_cif_fob_ratio"]) & ~gB.drift_fired
out["S-B_cells_detected_raw"] = int(gB.det_raw.sum())
out["S-B_cells_R4_fired"] = int(gB.rule_hits.apply(lambda h: "R4_cif_fob_ratio" in hits(h)).sum())
out["S-B_cells_only_R4"] = int(only_r4.sum())
out["S-B_material_cells_only_R4"] = int((only_r4 & (gB.max_rdm > 0.01)).sum())
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps(out, indent=1))
