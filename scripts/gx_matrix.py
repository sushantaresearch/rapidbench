"""V1b full pass: Great Expectations suite vs all 12 injector classes + control.
Writes results/gx_matrix.csv and docs/GX_MATRIX.md. Offline, seed=42, p=0.05."""
import os, sys, time, warnings
os.environ["TQDM_DISABLE"] = "1"
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
import logging
logging.disable(logging.CRITICAL)
import pandas as pd

from rapidbench.substrate import generate_synthetic_declarations
from rapidbench.injectors import INJECTORS
from rapidbench.validators.gx_adapter import gx_suite_fired

clean, fx = generate_synthetic_declarations(n=20000, seed=42)

rows = []
t0 = time.time()
fired = gx_suite_fired(clean, clean.copy())
rows.append({"injector": "CONTROL_clean", **fired,
             "any_fired": any(fired.values()), "runtime_s": round(time.time() - t0, 2)})
for name in sorted(INJECTORS):
    failed, _ = INJECTORS[name](clean, 0.05, 42, fx=fx)
    t0 = time.time()
    fired = gx_suite_fired(clean, failed)
    rows.append({"injector": name, **fired,
                 "any_fired": any(fired.values()), "runtime_s": round(time.time() - t0, 2)})

df = pd.DataFrame(rows)
df.to_csv("results/gx_matrix.csv", index=False)

short = {"expect_column_values_to_match_regex": "regex(hs6)",
         "expect_column_values_to_be_between": "between",
         "expect_compound_columns_to_be_unique": "compound_unique"}
lines = ["# V1b: Great Expectations 1.18.2 suite vs injector classes",
         "", "Synthetic substrate, n=20000, seed=42, severity p=0.05. Suite: hs6",
         "6-digit regex; non-negative bounds on qty/cif/fob/duty; compound",
         "uniqueness on (declaration_id, amendment_no). Same reference-free",
         "posture as production GX deployments: expectations encode schema",
         "knowledge, not a clean-reference comparison.", "",
         "| Injector | " + " | ".join(short.values()) + " | any |",
         "|---|---|---|---|---|"]
for r in rows:
    lines.append("| " + r["injector"] + " | " +
                 " | ".join("YES" if r[k] else "-" for k in short) +
                 " | " + ("**YES**" if r["any_fired"] else "no") + " |")
det = [r["injector"] for r in rows[1:] if r["any_fired"]]
mis = [r["injector"] for r in rows[1:] if not r["any_fired"]]
lines += ["", f"Detected {len(det)}/12: " + ", ".join(det),
          "", f"Missed {len(mis)}/12: " + ", ".join(mis),
          "", "Control fired: " + str(rows[0]["any_fired"]) +
          " (must be False; zero false alarms on clean data)."]
open("docs/GX_MATRIX.md", "w").write("\n".join(lines) + "\n")
print(f"GX matrix: {len(det)}/12 detected, control_fired={rows[0]['any_fired']}")
print("missed:", ", ".join(mis))
