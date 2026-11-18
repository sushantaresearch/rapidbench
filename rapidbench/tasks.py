"""Oracle revenue and compliance statistics (the quantities a revenue-analytics
pipeline is supposed to report). Each statistic is recomputed from the frame it
is given, so injected defects propagate exactly as they would in production.
"""
from __future__ import annotations

import pandas as pd


def s1_total_duty(df: pd.DataFrame) -> float:
    return float(df["duty_paid_usd"].sum())


def s2_duty_by_chapter(df: pd.DataFrame) -> dict[str, float]:
    ch = df["hs6"].astype(str).str.zfill(1).str[:2]  # derive from hs6 as pipelines do
    return df.groupby(ch)["duty_paid_usd"].sum().to_dict()


def s3_effective_duty_rate(df: pd.DataFrame) -> float:
    tot_cif = float(df["cif_usd"].sum())
    return float(df["duty_paid_usd"].sum()) / tot_cif if tot_cif else float("nan")


def s4_undervaluation_screen_rate(df: pd.DataFrame) -> float:
    uv = df["cif_usd"] / df["qty"]
    med = uv.groupby(df["hs6"]).transform("median")
    return float((uv < 0.5 * med).mean())


def s5_top_origin_duty_share(df: pd.DataFrame) -> float:
    by = df.groupby("origin_iso3")["duty_paid_usd"].sum()
    tot = float(by.sum())
    return float(by.max()) / tot if tot else float("nan")


def s6_flag_precision(df: pd.DataFrame) -> float:
    flagged = df[df["risk_flag"] == 1]
    return float(flagged["undervalued_outcome"].mean()) if len(flagged) else float("nan")


STATISTICS = {
    "S1_total_duty": s1_total_duty,
    "S2_duty_by_chapter": s2_duty_by_chapter,
    "S3_effective_duty_rate": s3_effective_duty_rate,
    "S4_uv_screen_rate": s4_undervaluation_screen_rate,
    "S5_top_origin_share": s5_top_origin_duty_share,
    "S6_flag_precision": s6_flag_precision,
}


def compute_all(df: pd.DataFrame, include: list[str] | None = None) -> dict:
    names = include if include is not None else list(STATISTICS)
    return {name: STATISTICS[name](df) for name in names}


# --- E1 contract oracle (matches prompts/pipeline_gen_prompt.md v0.2) --------

def e1_oracle(df: pd.DataFrame) -> dict:
    ch = df["hs6"].astype(str).str[:2]
    tot = float(df["duty_paid_usd"].sum())
    uv = df["cif_usd"] / df["qty"]
    med = uv.groupby(df["hs6"]).transform("median")
    by_origin = df.groupby("origin_iso3")["duty_paid_usd"].sum()
    return {
        "s1_duty_by_month": df.groupby("month")["duty_paid_usd"].sum().to_dict(),
        "s2_chapter_duty_share": (df.groupby(ch)["duty_paid_usd"].sum() / tot).to_dict(),
        "s3_effective_duty_rate": tot / float(df["cif_usd"].sum()),
        "s4_uv_below_half_median_share": float((uv < 0.5 * med).mean()),
        "s5_top_origin_duty_share": float(by_origin.max()) / tot,
    }
