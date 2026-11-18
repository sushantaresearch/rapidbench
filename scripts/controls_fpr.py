"""Clean-control FPR over seeds 42..46 for V1 (rules), V1b (GX), V2
(Evidently). Every tier must be silent on clean-vs-clean at every seed;
this is the paper's false-alarm claim. Writes docs/CONTROLS_FPR.md."""
import os, sys, warnings
os.environ["TQDM_DISABLE"] = "1"
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
import logging
logging.disable(logging.CRITICAL)
import pandas as pd

from rapidbench.substrate import generate_synthetic_declarations
from rapidbench.validators.rules import RuleValidator
from rapidbench.validators.evidently_adapter import evidently_drift_fired
from rapidbench.validators.gx_adapter import gx_suite_fired

SEEDS = [42, 43, 44, 45, 46]
rows = []
for seed in SEEDS:
    clean, _ = generate_synthetic_declarations(n=20000, seed=seed)
    cur = clean.copy()
    hits = RuleValidator(clean).run(cur)
    v1 = any(hits.values())
    v1b = any(gx_suite_fired(clean, cur).values())
    v2, share = evidently_drift_fired(clean, cur)
    rows.append({"seed": seed, "V1_rules_fired": v1,
                 "V1_hits": ";".join(k for k, f in hits.items() if f) or "-",
                 "V1b_gx_fired": v1b, "V2_drift_fired": v2,
                 "V2_drift_share": round(share, 4)})

df = pd.DataFrame(rows)
df.to_csv("results/controls_fpr.csv", index=False)
fpr = {t: df[c].mean() for t, c in [("V1", "V1_rules_fired"),
                                    ("V1b", "V1b_gx_fired"),
                                    ("V2", "V2_drift_fired")]}
lines = ["# Clean-control false positives, seeds 42-46 (n=20000 each)",
         "", "Each tier evaluated clean-vs-clean. Any firing here is a false",
         "alarm; detection numbers in the grid are only meaningful against a",
         "zero-FP baseline. R9 (unit-value extreme rate) was calibrated on the",
         "clean reference precisely to hold this at zero.", "",
         df.to_markdown(index=False), "",
         "FPR over 5 seeds: " + ", ".join(f"{t}={v:.0%}" for t, v in fpr.items())]
open("docs/CONTROLS_FPR.md", "w").write("\n".join(lines) + "\n")
print("FPR:", {t: f"{v:.0%}" for t, v in fpr.items()})
