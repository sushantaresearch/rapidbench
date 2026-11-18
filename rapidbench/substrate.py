"""Substrates for RAPID-Bench.

Primary smoke/dev substrate: seeded synthetic customs import declarations with a
DATE-like schema. Loaders for the real substrates (UN Comtrade mirror extracts,
DATE public synthetic customs data, CTGAN-generated declarations) are pluggable
and must be pointed at locally held files; nothing is downloaded silently.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CHAPTERS = ["01", "02", "03", "08", "10", "27", "29", "30",
            "39", "52", "61", "62", "72", "84", "85", "87"]

TARIFF = {"01": 0.05, "02": 0.05, "03": 0.10, "08": 0.15, "10": 0.02,
          "27": 0.00, "29": 0.03, "30": 0.00, "39": 0.10, "52": 0.07,
          "61": 0.20, "62": 0.20, "72": 0.05, "84": 0.01, "85": 0.03,
          "87": 0.25}

ISO3 = ["CHN", "IND", "USA", "JPN", "DEU", "SGP", "KOR", "MYS", "THA", "VNM",
        "IDN", "TUR", "ARE", "GBR", "ITA", "FRA", "BRA", "AUS", "NLD", "SAU"]

CURRENCIES = ["USD", "EUR", "JPY", "CNY"]


def _hs6_pool(rng: np.random.Generator, per_chapter: int = 4) -> list[str]:
    pool = []
    for ch in CHAPTERS:
        for _ in range(per_chapter):
            pool.append(ch + f"{rng.integers(0, 10000):04d}")
    return sorted(set(pool))


def fx_table(months: list[str], seed: int = 7) -> pd.DataFrame:
    """Monthly FX rate (local currency per USD) per non-USD currency."""
    rng = np.random.default_rng(seed)
    base = {"EUR": 0.92, "JPY": 155.0, "CNY": 7.2, "USD": 1.0}
    rows = []
    for m in months:
        for c in CURRENCIES:
            drift = 1.0 + rng.normal(0, 0.015)
            rows.append({"month": m, "currency": c, "rate": base[c] * drift})
    return pd.DataFrame(rows)


def generate_synthetic_declarations(n: int = 20000, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (declarations df, fx table). Deterministic given (n, seed)."""
    rng = np.random.default_rng(seed)
    months = [str(p) for p in pd.period_range("2024-01", periods=24, freq="M")]
    hs_pool = _hs6_pool(rng)

    hs6 = rng.choice(hs_pool, size=n)
    chapter = pd.Series(hs6).str[:2]
    month = rng.choice(months, size=n)
    origin = rng.choice(ISO3, size=n, p=_origin_weights(rng))
    currency = rng.choice(CURRENCIES, size=n, p=[0.55, 0.20, 0.10, 0.15])
    importer = rng.integers(1000, 1400, size=n).astype(str)

    cif = np.exp(rng.normal(9.2, 1.1, size=n))              # USD
    freight_ins = rng.uniform(0.04, 0.12, size=n)
    fob = cif / (1.0 + freight_ins)
    qty = np.maximum(np.exp(rng.normal(4.5, 1.3, size=n)), 1.0)

    duty_rate = chapter.map(TARIFF).to_numpy()
    duty_paid = cif * duty_rate

    df = pd.DataFrame({
        "decl_id": [f"D{seed}{i:07d}" for i in range(n)],
        "month": month,
        "hs6": hs6,
        "chapter": chapter.to_numpy(),
        "origin_iso3": origin,
        "importer_id": importer,
        "currency": currency,
        "cif_usd": cif,
        "fob_usd": fob,
        "qty": qty,
        "duty_rate": duty_rate,
        "duty_paid_usd": duty_paid,
    })

    # Latent undervaluation outcome + an imperfect risk flag (for leakage tasks).
    uv = df["cif_usd"] / df["qty"]
    med = uv.groupby(df["hs6"]).transform("median")
    outcome = (uv < 0.45 * med).astype(int)
    noise = rng.random(n)
    flag = np.where(noise < 0.15, 1 - outcome, outcome)  # ~85% agreement
    df["undervalued_outcome"] = outcome
    df["risk_flag"] = flag

    return df, fx_table(months, seed=seed + 1)


def _origin_weights(rng: np.random.Generator) -> np.ndarray:
    w = rng.uniform(0.5, 3.0, size=len(ISO3))
    return w / w.sum()


# ---------------------------------------------------------------------------
# Real-substrate loaders (user supplies local paths; schemas normalised to the
# column set above). Kept as thin, explicit functions so provenance is logged.
# ---------------------------------------------------------------------------

def load_comtrade_extract(path: str) -> pd.DataFrame:
    """Load a locally saved UN Comtrade extract (CSV) and normalise columns.
    Expects at least: period, cmdCode, reporterISO/partnerISO, primaryValue.
    """
    raw = pd.read_csv(path, dtype={"cmdCode": str})
    raise NotImplementedError(
        "Map your Comtrade extract columns here before E-grid runs; "
        "kept explicit to avoid silent schema assumptions.")


def load_date_substrate(path: str) -> pd.DataFrame:
    """Public DATE synthetic customs imports (Kim et al.; Seondong/
    Customs-Fraud-Detection, data/synthetic-imports-declarations.csv).

    100,000 single-item declarations, 2013, 12 months. HS codes are stored
    with leading zeros stripped (9-digit rows are chapters 01-09); restored
    via zfill(10). No currency column (F03 not applicable) and no ex-ante
    risk flag (F06/S6 not applicable). duty_rate is the per-row effective
    rate total.taxes/cif.value so that injectors recomputing
    duty = cif * rate stay internally consistent.
    """
    raw = pd.read_csv(path, dtype={"tariff.code": str})
    hs10 = raw["tariff.code"].str.zfill(10)
    cif = raw["cif.value"].astype(float)
    rate = (raw["total.taxes"].astype(float) / cif.replace(0, np.nan)).fillna(0.0)
    df = pd.DataFrame({
        "decl_id": raw["sgd.id"].astype(str),
        "month": "20" + raw["sgd.date"].str[:5],           # YY-MM-DD -> 20YY-MM
        "hs6": hs10.str[:6],
        "origin_iso3": raw["country"].astype(str),
        "importer_id": raw["importer.id"].astype(str),
        "cif_usd": cif,
        "fob_usd": raw["fob.value"].astype(float),
        "qty": raw["quantity"].astype(float).clip(lower=1.0),
        "duty_rate": rate,
        "duty_paid_usd": raw["total.taxes"].astype(float),
        "undervalued_outcome": raw["illicit"].astype(int),
    })
    df["chapter"] = df["hs6"].str[:2]
    return df.reset_index(drop=True)


def load_ctgan_substrate(path: str) -> pd.DataFrame:
    """Public CTGAN-generated Korea Customs import declarations
    (Jeong, Kim et al., arXiv:2208.02484; Seondong/Customs-Declaration-Datasets,
    data/df_syn_eng.csv, MIT licence).

    54,000 declarations, 22 attributes, 18 months (2020-01..2021-06). Monetary
    unit is KRW; all RDM statistics are relative so the unit is immaterial.
    No currency column (F03 n/a), no FOB/CIF pair (F04/F10 n/a), no ex-ante
    risk flag (F06/S6 n/a). Native ad-valorem Tax Rate drives duty;
    duty_paid_usd is derived as value * rate (declared duty is not released).
    Rows with non-positive mass or price are dropped and counted.
    """
    raw = pd.read_csv(path, dtype={"HS6 Code": str})
    keep = (raw["Net Mass"] > 0) & (raw["Item Price"] > 0)
    dropped = int((~keep).sum())
    raw = raw[keep]
    price = raw["Item Price"].astype(float)
    rate = raw["Tax Rate"].astype(float) / 100.0
    df = pd.DataFrame({
        "decl_id": raw["Declaration ID"].astype(str),
        "month": raw["Date"].str[:7],
        "hs6": raw["HS6 Code"].str.zfill(6),
        "origin_iso3": raw["Country of Origin"].astype(str),
        "importer_id": raw["Importer ID"].astype(str),
        "cif_usd": price,
        "qty": raw["Net Mass"].astype(float),
        "duty_rate": rate,
        "duty_paid_usd": price * rate,
        "undervalued_outcome": raw["Fraud"].astype(int),
    })
    df["chapter"] = df["hs6"].str[:2]
    df.attrs["rows_dropped_nonpositive"] = dropped
    return df.reset_index(drop=True)
