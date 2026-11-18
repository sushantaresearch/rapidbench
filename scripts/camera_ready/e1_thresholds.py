"""E1 self-test verdicts at the 0.5% and 1% materiality gates (the paper says the artifact
reports both). Re-runs the four hand-written pipelines of scripts/e1_selftest.py through the
real subprocess path (no API calls) and classifies each at both gates.
Usage: python3 -I e1_thresholds.py <rapidbench_repo_dir> <out_csv>"""
import sys, tempfile, importlib.util
REPO, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, REPO)
import pandas as pd
from rapidbench.substrate import generate_synthetic_declarations
from rapidbench.tasks import e1_oracle
from rapidbench.executor import run_pipeline, score_pipeline, classify
src = open(REPO + "/scripts/e1_selftest.py").read()
ns = {}
exec(src.split("clean, _ = generate_synthetic_declarations")[0].replace('sys.path.insert(0, ".")', ""), ns)
PIPES = ns["PIPES"]
clean, _ = generate_synthetic_declarations(n=20000, seed=42)
oracle = e1_oracle(clean)
with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
    clean.to_csv(f.name, index=False); csv_path = f.name
rows = []
for name, code in PIPES.items():
    res = run_pipeline(code, csv_path)
    sc = score_pipeline(res["stats"], oracle) if res["ok"] else None
    rows.append({"pipeline": name, **({f"rdm_{k[:2]}_pct": round(100 * v, 3) for k, v in sc.items()} if sc else {}),
                 "verdict_at_1pct": classify(res, sc, material=0.01),
                 "verdict_at_0.5pct": classify(res, sc, material=0.005)})
df = pd.DataFrame(rows); df.to_csv(OUT, index=False); print(df.to_string(index=False))
