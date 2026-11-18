"""RAPID-Bench smoke test: 20k synthetic declarations, all 12 injectors at
p=0.05 (single seed), rule-validator detection, RDM profile per statistic.
Writes docs/SMOKE_RESULTS.md. These are scaffold-verification numbers, not
paper results (paper grid = 3 substrates x 12 classes x 3 severities x 5 seeds).
"""
import sys, time
sys.path.insert(0, ".")
import pandas as pd

from rapidbench.substrate import generate_synthetic_declarations
from rapidbench.tasks import compute_all
from rapidbench.injectors import INJECTORS
from rapidbench.metrics import rdm_profile, is_silent, detection_summary
from rapidbench.validators.rules import RuleValidator
from rapidbench.validators.evidently_adapter import evidently_drift_fired
import warnings; warnings.filterwarnings("ignore")

P, SEED = 0.05, 42
t0 = time.time()
clean, fx = generate_synthetic_declarations(n=20000, seed=SEED)
oracle = compute_all(clean)
validator = RuleValidator(clean)

fp = [r for r, f in validator.run(clean).items() if f]
ev_fp, _ = evidently_drift_fired(clean, clean.copy())
rows = []
for name, fn in INJECTORS.items():
    failed, meta = fn(clean, P, SEED, fx=fx)
    prof = rdm_profile(compute_all(failed), oracle)
    detected, hits = detection_summary(validator.run(failed))
    drift_fired, drift_share = evidently_drift_fired(clean, failed)
    any_detected = detected or drift_fired
    rows.append({
        "injector": name,
        "rows_affected": meta["rows_affected"],
        "max_RDM_%": round(100 * max(prof.values()), 2),
        "worst_stat": max(prof, key=prof.get),
        "S1_duty_%": round(100 * prof["S1_total_duty"], 2),
        "rules": detected,
        "drift": drift_fired,
        "rules_fired": ",".join(hits) if hits else "-",
        "SILENT": is_silent(prof, any_detected),
    })

res = pd.DataFrame(rows)
elapsed = time.time() - t0
md = ["# RAPID-Bench smoke test (real run)",
      f"n=20000 synthetic declarations, p={P}, seed={SEED}, "
      f"runtime {elapsed:.1f}s, pandas {pd.__version__}.",
      f"False positives on clean data: rules={fp if fp else 'none'}; "
      f"evidently control fired={ev_fp}.",
      "", res.to_markdown(index=False), "",
      "Silent = max RDM > 1% with neither rule nor drift tier firing. Scaffold verification "
      "only; not paper results."]
open("docs/SMOKE_RESULTS.md", "w").write("\n".join(md))
print(res.to_string(index=False))
print(f"\nclean-data false positives: {fp if fp else 'none'} | {elapsed:.1f}s")
