"""Clean-vs-clean controls on the public substrates (S-B DATE, S-C CTGAN).

Writes results/controls_real.csv with one row per (substrate, tier) and, for
rules, the names of any checks that fire on the untouched clean frame. Rules
that fire on clean data carry no detection information on that substrate;
grid detection is scored net of them (see scripts/net_detection.py).
"""
import pandas as pd
from rapidbench.substrate import load_date_substrate, load_ctgan_substrate
from rapidbench.validators.rules import RuleValidator
from rapidbench.validators.evidently_adapter import evidently_drift_fired

SUBS = [("date", load_date_substrate, "data/date_synthetic.csv"),
        ("ctgan", load_ctgan_substrate, "data/ctgan_declarations.csv")]

rows = []
for name, loader, path in SUBS:
    clean = loader(path)
    fired = RuleValidator(clean).run(clean)
    hits = sorted(k for k, v in fired.items() if v)
    d_fired, d_share = evidently_drift_fired(clean, clean)
    rows.append({"substrate": name, "tier": "V1_rules",
                 "fired": bool(hits), "hits": ";".join(hits)})
    rows.append({"substrate": name, "tier": "V2_drift",
                 "fired": bool(d_fired), "hits": f"share={d_share:.3f}"})

out = pd.DataFrame(rows)
out.to_csv("results/controls_real.csv", index=False)
print(out.to_string(index=False))
