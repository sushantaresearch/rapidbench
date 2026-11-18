"""Rule-based validator family (V1 in the detection matrix).

Nine deterministic checks representative of what a competent data engineer
would encode in Great Expectations or dbt tests for a customs revenue mart.
All baselines (row counts, chapter shares, duplicate rates, the tariff table
and the origin vocabulary) are learned from the clean reference frame,
mirroring production practice where tests are configured against the current
trusted mart. Checks whose required columns are absent from a substrate
(e.g. no FOB column) are skipped as not applicable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class RuleValidator:
    def __init__(self, reference: pd.DataFrame):
        self.ref_rows = len(reference)
        ch = reference["hs6"].str[:2]
        self.ref_shares = (reference.groupby(ch)["duty_paid_usd"].sum()
                           / reference["duty_paid_usd"].sum())
        self.ref_dup_rate = self._biz_dup_rate(reference)
        self.has_fob = "fob_usd" in reference.columns
        if self.has_fob:
            self.ref_ratio_med = float(
                (reference["cif_usd"] / reference["fob_usd"]).median())
        self.ref_uv_extreme = self._uv_extreme_rate(reference)
        # Reference-learned tariff table: modal duty rate per hs6, plus the
        # clean frame's own mismatch rate against that table (real tariffs
        # vary within hs6 across regimes, e.g. MFN vs FTA lines).
        self.ref_rate = reference.groupby("hs6")["duty_rate"].agg(
            lambda s: s.mode().iloc[0])
        self.ref_rate_mismatch = self._rate_mismatch(reference)
        # Reference-learned origin vocabulary.
        self.ref_vocab = set(reference["origin_iso3"].unique())

    @staticmethod
    def _uv_extreme_rate(df: pd.DataFrame) -> float:
        uv = df["cif_usd"] / df["qty"]
        med_uv = uv.groupby(df["hs6"]).transform("median")
        return float(((uv < 0.05 * med_uv) | (uv > 20 * med_uv)).mean())

    @staticmethod
    def _biz_dup_rate(df: pd.DataFrame) -> float:
        key = ["importer_id", "hs6", "month", "qty", "cif_usd"]
        return float(df.duplicated(subset=key).mean())

    def _rate_mismatch(self, df: pd.DataFrame) -> float:
        expected = df["hs6"].map(self.ref_rate)
        with np.errstate(invalid="ignore"):
            mismatch = ~np.isclose(df["duty_rate"], expected.fillna(-1), atol=1e-9)
        return float(mismatch.mean())

    def run(self, df: pd.DataFrame) -> dict[str, bool]:
        fired: dict[str, bool] = {}

        hs = df["hs6"].astype(str)
        fired["R1_hs_format"] = bool(((hs.str.len() != 6) | (~hs.str.isdigit())).mean() > 0.001)
        fired["R2_positive_value"] = bool((df["cif_usd"] <= 0).mean() > 0.001)

        fired["R3_duplicate_keys"] = bool(
            self._biz_dup_rate(df) > self.ref_dup_rate + 0.002)

        if self.has_fob and "fob_usd" in df.columns:
            ratio = df["cif_usd"] / df["fob_usd"]
            med = float(ratio.median())
            fired["R4_cif_fob_ratio"] = bool(med < 1.02 or med > 1.30 or
                                             float((ratio <= 1.0 + 1e-9).mean()) > 0.02)

        fired["R5_tariff_join_coverage"] = bool(
            self._rate_mismatch(df) > self.ref_rate_mismatch + 0.005)

        fired["R6_row_reconciliation"] = bool(
            abs(len(df) - self.ref_rows) / self.ref_rows > 0.005)

        ch = df["hs6"].astype(str).str[:2]
        tot = df["duty_paid_usd"].sum()
        shares = df.groupby(ch)["duty_paid_usd"].sum() / tot if tot else pd.Series(dtype=float)
        l1 = float((shares.reindex(self.ref_shares.index.union(shares.index), fill_value=0)
                    - self.ref_shares.reindex(self.ref_shares.index.union(shares.index),
                                              fill_value=0)).abs().sum())
        fired["R7_chapter_share_drift"] = bool(l1 > 0.05)

        fired["R8_iso3_vocabulary"] = bool(
            (~df["origin_iso3"].isin(self.ref_vocab)).mean() > 0.001)

        fired["R9_unit_value_bounds"] = bool(
            self._uv_extreme_rate(df) > self.ref_uv_extreme + 0.005)

        return fired


RULE_NAMES = ["R1_hs_format", "R2_positive_value", "R3_duplicate_keys",
              "R4_cif_fob_ratio", "R5_tariff_join_coverage",
              "R6_row_reconciliation", "R7_chapter_share_drift",
              "R8_iso3_vocabulary", "R9_unit_value_bounds"]
