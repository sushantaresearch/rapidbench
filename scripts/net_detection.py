"""Derive net-of-clean-firing detection for the S-B (DATE) grid.

A rule that fires on the substrate's untouched clean frame cannot signal a
fault on that substrate; its alarm is background. Detection is therefore
scored over the remaining rule hits, union drift. Controls
(results/controls_real.csv) identify the clean-firing set per substrate.
S-A and S-C have empty clean-firing sets, so raw equals net there.
"""
import pandas as pd

ctl = pd.read_csv("results/controls_real.csv")
clean_firing = {}
for _, r in ctl[ctl.tier == "V1_rules"].iterrows():
    clean_firing[r.substrate] = set(str(r.hits).split(";")) if r.fired else set()

g = pd.read_csv("results/grid_date.csv")
cf = clean_firing.get("date", set())

def net_hits(h):
    if pd.isna(h) or not h:
        return []
    return [x for x in str(h).split(";") if x and x not in cf]

g["net_hits"] = g.rule_hits.apply(net_hits)
g["rules_net"] = g.net_hits.str.len() > 0
g["detected_net"] = g.rules_net | g.drift_fired
g["silent_net"] = (~g.detected_net) & (g.max_rdm > 0.01)
g.to_csv("results/grid_date_net.csv", index=False)
print("clean-firing on date:", sorted(cf))
print("net silent:", int(g.silent_net.sum()), "/", len(g))
