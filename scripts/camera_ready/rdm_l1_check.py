"""Recompute F01 (p=0.20, seed 42, synthetic) chapter-duty RDM and the reallocated share mass.
Usage: python3 -I rdm_l1_check.py <rapidbench_repo_dir> <out.json>"""
import sys, json
sys.path.insert(0, sys.argv[1])
from rapidbench.substrate import generate_synthetic_declarations
from rapidbench.injectors import INJECTORS
from rapidbench.tasks import s2_duty_by_chapter, s1_total_duty
from rapidbench.metrics import rdm
import yaml
cfg = yaml.safe_load(open(sys.argv[1] + "/configs/grid.yaml"))
n = [s for s in cfg["substrates"] if s.get("name") == "synthetic"][0].get("n", 20000) if isinstance(cfg.get("substrates"), list) else cfg.get("n", 20000)
df, fx = generate_synthetic_declarations(n=n, seed=42)
o = s2_duty_by_chapter(df)
bad = INJECTORS["F01_hs_leading_zero_loss"](df.copy(), 0.20, 42, fx=fx)
bad = bad[0] if isinstance(bad, tuple) else bad
f = s2_duty_by_chapter(bad)
To, Tf = s1_total_duty(df), s1_total_duty(bad)
keys = set(o) | set(f)
so = {k: o.get(k, 0.0) / To for k in keys}; sf = {k: f.get(k, 0.0) / Tf for k in keys}
l1_share = sum(abs(sf[k] - so[k]) for k in keys)
moved = sum(max(so[k] - sf[k], 0) for k in keys)   # share mass leaving its original chapter
res = {"n": n, "rdm_S2": rdm(f, o), "total_duty_oracle": To, "total_duty_fail": Tf,
       "l1_between_share_vectors": l1_share, "reallocated_share_mass": moved,
       "ratio_rdm_over_moved": rdm(f, o) / moved}
print(json.dumps(res, indent=1)); json.dump(res, open(sys.argv[2], "w"), indent=1)
