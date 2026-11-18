"""V1b cross-substrate pass: GX suite vs applicable injector classes on the
public substrates (DATE, CTGAN), seed 42, p=0.05, matching gx_matrix.py's
design point on S-A. Writes results/gx_matrix_cross.csv."""
import os, sys, time, warnings
os.environ["TQDM_DISABLE"] = "1"
sys.path.insert(0, ".")
warnings.filterwarnings("ignore")
import logging
logging.disable(logging.CRITICAL)
import pandas as pd

from rapidbench.substrate import load_date_substrate, load_ctgan_substrate
from rapidbench.injectors import INJECTORS
from rapidbench.runner import INJECTOR_REQUIRES
from rapidbench.validators.gx_adapter import gx_suite_fired

SUBS = [("date", load_date_substrate, "data/date_synthetic.csv"),
        ("ctgan", load_ctgan_substrate, "data/ctgan_declarations.csv")]

rows = []
for sub, loader, path in SUBS:
    clean = loader(path)
    cols = set(clean.columns)
    t0 = time.time()
    fired = gx_suite_fired(clean, clean.copy())
    rows.append({"substrate": sub, "injector": "CONTROL_clean", **fired,
                 "any_fired": any(fired.values()),
                 "runtime_s": round(time.time() - t0, 2)})
    for name in sorted(INJECTORS):
        if not INJECTOR_REQUIRES.get(name, set()) <= cols:
            continue
        failed, _ = INJECTORS[name](clean, 0.05, 42, fx=None)
        t0 = time.time()
        fired = gx_suite_fired(clean, failed)
        rows.append({"substrate": sub, "injector": name, **fired,
                     "any_fired": any(fired.values()),
                     "runtime_s": round(time.time() - t0, 2)})
    det = [r["injector"] for r in rows if r["substrate"] == sub
           and r["injector"] != "CONTROL_clean" and r["any_fired"]]
    n = sum(1 for r in rows if r["substrate"] == sub
            and r["injector"] != "CONTROL_clean")
    ctrl = [r for r in rows if r["substrate"] == sub
            and r["injector"] == "CONTROL_clean"][0]["any_fired"]
    print(f"{sub}: detected {len(det)}/{n}  control_fired={ctrl}  -> {', '.join(det) or 'none'}")

pd.DataFrame(rows).to_csv("results/gx_matrix_cross.csv", index=False)
print("written results/gx_matrix_cross.csv")
