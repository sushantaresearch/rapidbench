"""E1 harness self-test (no API key needed): three hand-written pipelines,
one correct and two seeded with realistic intrinsic defects, executed through
the real subprocess path and scored against the oracle. Proves the harness
separates correct from defective code before any LLM panel runs.
Writes docs/E1_SELFTEST.md."""
import sys, tempfile, json
sys.path.insert(0, ".")
import pandas as pd
from rapidbench.substrate import generate_synthetic_declarations
from rapidbench.tasks import e1_oracle
from rapidbench.executor import run_pipeline, score_pipeline, classify

HEADER = """import sys, json
import pandas as pd
df = pd.read_csv(sys.argv[1]{read_kw})
ch = df["hs6"].astype(str).str[:2]
tot = float(df["duty_paid_usd"].sum())
uv = df["cif_usd"] / df["qty"]
med = uv.groupby(df["hs6"]).transform("median")
out = {{
 "s1_duty_by_month": df.groupby("month")["duty_paid_usd"].sum().to_dict(),
 "s2_chapter_duty_share": (df.groupby(ch)["duty_paid_usd"].sum()/tot).to_dict(),
 "s3_effective_duty_rate": {s3},
 "s4_uv_below_half_median_share": float((uv < 0.5*med).mean()),
 "s5_top_origin_duty_share": float(df.groupby("origin_iso3")["duty_paid_usd"].sum().max())/tot,
}}
print(json.dumps(out))"""

PIPES = {
  "P_ref_correct": HEADER.format(read_kw=', dtype={"hs6": str}',
                                 s3='tot / float(df["cif_usd"].sum())'),
  # forgets dtype=str: hs6 leading zeros lost on read (intrinsic F01)
  "P_bug_hs_dtype": HEADER.format(read_kw="",
                                  s3='tot / float(df["cif_usd"].sum())'),
  # mean-of-ratios instead of ratio-of-sums (classic aggregation defect)
  "P_bug_rate_agg": HEADER.format(read_kw=', dtype={"hs6": str}',
                                  s3='float((df["duty_paid_usd"]/df["cif_usd"]).mean())'),
  # FOB used as the value denominator (intrinsic CIF/FOB conflation)
  "P_bug_fob_denom": HEADER.format(read_kw=', dtype={"hs6": str}',
                                   s3='tot / float(df["fob_usd"].sum())'),
}

clean, _ = generate_synthetic_declarations(n=20000, seed=42)
oracle = e1_oracle(clean)
with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
    clean.to_csv(f.name, index=False); csv_path = f.name

rows = []
for name, code in PIPES.items():
    res = run_pipeline(code, csv_path)
    scores = score_pipeline(res["stats"], oracle) if res["ok"] else None
    verdict = classify(res, scores)
    rows.append({"pipeline": name, "ok": res["ok"],
                 **({f"rdm_{k[:2]}_%": round(100*v, 3) for k, v in scores.items()} if scores else {}),
                 "verdict": verdict, "error": res["error"] or "-"})
res_df = pd.DataFrame(rows)
md = ["# E1 harness self-test (real subprocess runs)",
      "n=20000 synthetic declarations, seed=42. Correct pipeline must score "
      "~0 RDM on every statistic; seeded-defect pipelines must classify as "
      "defective on exactly the statistics their bug touches. Note the "
      "mean-of-ratios case: a real bug landing under the 1% materiality "
      "threshold and passing as correct, a threshold-sensitivity finding "
      "the paper will report.", "",
      res_df.to_markdown(index=False)]
open("docs/E1_SELFTEST.md", "w").write("\n".join(md))
print(res_df.to_string(index=False))
