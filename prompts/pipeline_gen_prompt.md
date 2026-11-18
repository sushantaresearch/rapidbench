# E1 pipeline-generation prompt (frozen template v0.2)

System: You are a data engineer at a customs administration. Write a complete,
runnable pandas pipeline. Return only code, no prose, no markdown fences.

User: A declarations CSV has columns {decl_id, month, hs6, chapter,
origin_iso3, importer_id, currency, cif_usd, fob_usd, qty, duty_rate,
duty_paid_usd, undervalued_outcome, risk_flag}. Write a Python script that
reads the CSV path from sys.argv[1] and prints, as the final line of stdout,
exactly one JSON object with these keys:
  s1_duty_by_month: total duty_paid_usd per month (object keyed by month)
  s2_chapter_duty_share: each HS chapter's share of total duty (object)
  s3_effective_duty_rate: total duty divided by total CIF value (number)
  s4_uv_below_half_median_share: share of declarations whose unit value
    (cif_usd/qty) is below half the median unit value of the same hs6 (number)
  s5_top_origin_duty_share: the largest single origin country's share of total
    duty (number)

Protocol: k=3 samples per model per task variant, temperature 0.2, panel and
versions logged to results/e1_manifest.json. Each sample is executed by
rapidbench/executor.py in an isolated interpreter against clean and injected
substrates; reported statistics are diffed against tasks.e1_oracle to measure
intrinsic generation defects and injected-defect propagation. Outcome classes:
crash, contract_violation, correct, defective(stat list) at RDM > 1%.
