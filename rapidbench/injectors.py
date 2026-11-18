"""RAPID-Bench failure injectors.

Twelve failure classes observed in (or plausible for) AI-generated
revenue-analytics pipelines over customs/trade data. Each injector takes a
clean declarations frame plus severity p (fraction of rows touched where
applicable) and returns (df_failed, meta). All randomness is seeded.

Classes F1--F6 are domain-specific (the paper's contribution); F7--F12 are
generic data-engineering failures instantiated on revenue data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

Meta = dict


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _subset(df: pd.DataFrame, p: float, seed: int, mask=None) -> pd.Index:
    idx = df.index if mask is None else df.index[mask]
    k = max(1, int(round(p * len(idx))))
    return pd.Index(_rng(seed).choice(idx.to_numpy(), size=min(k, len(idx)), replace=False))


# --- Domain-specific classes -------------------------------------------------

def f01_hs_leading_zero_loss(df, p, seed, fx=None):
    """HS6 read as integer somewhere in the pipeline: leading zeros lost."""
    out = df.copy()
    m = out["hs6"].str.startswith("0")
    out.loc[m, "hs6"] = out.loc[m, "hs6"].astype(int).astype(str)
    return out, {"rows_affected": int(m.sum()), "note": "dtype cast, ignores p"}


def f02_unit_quantity_mismatch(df, p, seed, fx=None):
    """kg reported as g (x1000) on a subset: unit values collapse."""
    out = df.copy()
    sel = _subset(out, p, seed)
    out.loc[sel, "qty"] = out.loc[sel, "qty"] * 1000.0
    return out, {"rows_affected": len(sel)}


def f03_fx_stale_rate(df, p, seed, fx: pd.DataFrame = None):
    """Non-USD declarations converted with the previous month's FX rate."""
    out = df.copy()
    non_usd = out["currency"] != "USD"
    sel = _subset(out, p, seed, mask=non_usd)
    rate = fx.set_index(["month", "currency"])["rate"]
    months = sorted(fx["month"].unique())
    prev = {m: months[max(0, i - 1)] for i, m in enumerate(months)}
    cur = rate.loc[list(zip(out.loc[sel, "month"], out.loc[sel, "currency"]))].to_numpy()
    stale = rate.loc[[(prev[m], c) for m, c in
                      zip(out.loc[sel, "month"], out.loc[sel, "currency"])]].to_numpy()
    ratio = stale / cur
    out.loc[sel, "cif_usd"] = out.loc[sel, "cif_usd"] * ratio
    out.loc[sel, "duty_paid_usd"] = out.loc[sel, "cif_usd"] * out.loc[sel, "duty_rate"]
    return out, {"rows_affected": len(sel)}


def f04_cif_fob_conflation(df, p, seed, fx=None):
    """FOB used where CIF is required (valuation base error) on a subset."""
    out = df.copy()
    sel = _subset(out, p, seed)
    out.loc[sel, "cif_usd"] = out.loc[sel, "fob_usd"]
    out.loc[sel, "duty_paid_usd"] = out.loc[sel, "cif_usd"] * out.loc[sel, "duty_rate"]
    return out, {"rows_affected": len(sel)}


def f05_tariff_year_misjoin(df, p, seed, fx=None):
    """Duty rates joined from the wrong tariff-schedule vintage (all rows)."""
    out = df.copy()
    g = _rng(seed)
    wrong = {ch: max(0.0, r * g.uniform(0.7, 1.3)) for ch, r in
             out.groupby("chapter")["duty_rate"].first().items()}
    out["duty_rate"] = out["chapter"].map(wrong)
    out["duty_paid_usd"] = out["cif_usd"] * out["duty_rate"]
    return out, {"rows_affected": len(out), "note": "join-key vintage error, ignores p"}


def f06_outcome_leakage(df, p, seed, fx=None):
    """Post-clearance outcome leaks into the risk flag on a subset
    (temporal leakage: flag looks better than it is)."""
    out = df.copy()
    sel = _subset(out, p, seed)
    out.loc[sel, "risk_flag"] = out.loc[sel, "undervalued_outcome"]
    return out, {"rows_affected": len(sel)}


# --- Generic classes instantiated on revenue data ----------------------------

def f07_duplicate_amendments(df, p, seed, fx=None):
    """Amended declarations ingested alongside originals (partial dupes)."""
    out = df.copy()
    sel = _subset(out, p, seed)
    dup = out.loc[sel].copy()
    dup["decl_id"] = dup["decl_id"] + "-A"
    return pd.concat([out, dup], ignore_index=True), {"rows_affected": len(sel)}


def f08_null_zerofill(df, p, seed, fx=None):
    """Missing customs values imputed as zero on a subset."""
    out = df.copy()
    sel = _subset(out, p, seed)
    out.loc[sel, "cif_usd"] = 0.0
    out.loc[sel, "duty_paid_usd"] = 0.0
    return out, {"rows_affected": len(sel)}


def f09_partner_swap(df, p, seed, fx=None):
    """Origin country column permuted on a subset (wrong join order)."""
    out = df.copy()
    sel = _subset(out, p, seed)
    vals = out.loc[sel, "origin_iso3"].to_numpy()
    _rng(seed + 1).shuffle(vals)
    out.loc[sel, "origin_iso3"] = vals
    return out, {"rows_affected": len(sel)}


def f10_schema_drift_fallback(df, p, seed, fx=None):
    """Renamed value column; pipeline silently falls back to FOB (all rows)."""
    out = df.copy()
    out["cif_usd"] = out["fob_usd"]
    out["duty_paid_usd"] = out["cif_usd"] * out["duty_rate"]
    return out, {"rows_affected": len(out), "note": "rename+fallback, ignores p"}


def f11_dedup_overreach(df, p, seed, fx=None):
    """Aggressive dedup drops legitimate split shipments
    (same importer/hs6/month treated as duplicates)."""
    out = df.copy()
    before = len(out)
    out = out.drop_duplicates(subset=["importer_id", "hs6", "month"], keep="first")
    return out.reset_index(drop=True), {"rows_affected": before - len(out),
                                        "note": "ignores p"}


def f12_country_code_drift(df, p, seed, fx=None):
    """ISO3 codes replaced by numeric codes on a subset (mixed vocabularies)."""
    out = df.copy()
    sel = _subset(out, p, seed)
    num = {c: str(100 + i) for i, c in enumerate(sorted(df["origin_iso3"].unique()))}
    out.loc[sel, "origin_iso3"] = out.loc[sel, "origin_iso3"].map(num)
    return out, {"rows_affected": len(sel)}


INJECTORS = {
    "F01_hs_leading_zero_loss": f01_hs_leading_zero_loss,
    "F02_unit_qty_mismatch": f02_unit_quantity_mismatch,
    "F03_fx_stale_rate": f03_fx_stale_rate,
    "F04_cif_fob_conflation": f04_cif_fob_conflation,
    "F05_tariff_year_misjoin": f05_tariff_year_misjoin,
    "F06_outcome_leakage": f06_outcome_leakage,
    "F07_duplicate_amendments": f07_duplicate_amendments,
    "F08_null_zerofill": f08_null_zerofill,
    "F09_partner_swap": f09_partner_swap,
    "F10_schema_drift_fallback": f10_schema_drift_fallback,
    "F11_dedup_overreach": f11_dedup_overreach,
    "F12_country_code_drift": f12_country_code_drift,
}
