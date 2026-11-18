import sys, json
import pandas as pd
df = pd.read_csv(sys.argv[1])
ch = df["hs6"].astype(str).str[:2]
tot = float(df["duty_paid_usd"].sum())
uv = df["cif_usd"] / df["qty"]
med = uv.groupby(df["hs6"]).transform("median")
out = {
 "s1_duty_by_month": df.groupby("month")["duty_paid_usd"].sum().to_dict(),
 "s2_chapter_duty_share": (df.groupby(ch)["duty_paid_usd"].sum()/tot).to_dict(),
 "s3_effective_duty_rate": tot / float(df["cif_usd"].sum()),
 "s4_uv_below_half_median_share": float((uv < 0.5*med).mean()),
 "s5_top_origin_duty_share": float(df.groupby("origin_iso3")["duty_paid_usd"].sum().max())/tot,
}
print(json.dumps(out))