"""RAPID-Bench grid runner.

Paper grid: substrates x 12 failure classes x severities x seeds, scored by
each validator tier. Writes one tidy CSV per substrate under results/.

Usage:
    python3 -m rapidbench.runner --config configs/grid.yaml
"""
from __future__ import annotations

import argparse
import time
import warnings
from pathlib import Path

import pandas as pd
import yaml

from .injectors import INJECTORS

# Column requirements beyond the universal set; injectors are skipped as not
# applicable (n/a) on substrates lacking them.
INJECTOR_REQUIRES = {
    "F03_fx_stale_rate": {"currency"},
    "F04_cif_fob_conflation": {"fob_usd"},
    "F06_outcome_leakage": {"risk_flag"},
    "F10_schema_drift_fallback": {"fob_usd"},
}
STAT_REQUIRES = {"S6_flag_precision": {"risk_flag"}}
from .metrics import detection_summary, is_silent, rdm_profile
from .substrate import generate_synthetic_declarations
from .tasks import STATISTICS, compute_all
from .validators.rules import RuleValidator

warnings.filterwarnings("ignore")


def load_substrate(name: str, cfg: dict, seed: int):
    if name == "synthetic":
        return generate_synthetic_declarations(n=cfg.get("n", 20000), seed=seed)
    if name == "comtrade":
        from .substrate import load_comtrade_extract
        return load_comtrade_extract(cfg["path"]), None
    if name == "date":
        from .substrate import load_date_substrate
        return load_date_substrate(cfg["path"]), None
    if name == "ctgan":
        from .substrate import load_ctgan_substrate
        return load_ctgan_substrate(cfg["path"]), None
    raise ValueError(f"unknown substrate {name}")


def run(config_path: str) -> None:
    cfg = yaml.safe_load(open(config_path))
    out_dir = Path(cfg.get("out_dir", "results"))
    out_dir.mkdir(exist_ok=True)
    use_drift = cfg.get("validators", {}).get("evidently", True)
    if use_drift:
        from .validators.evidently_adapter import evidently_drift_fired

    for sub_name, sub_cfg in cfg["substrates"].items():
        if not sub_cfg.get("enabled", False):
            continue
        rows = []
        for seed in cfg["seeds"]:
            clean, fx = load_substrate(sub_name, sub_cfg, seed)
            cols = set(clean.columns)
            stats = [s for s in STATISTICS
                     if STAT_REQUIRES.get(s, set()) <= cols]
            oracle = compute_all(clean, include=stats)
            validator = RuleValidator(clean)
            for inj_name, fn in INJECTORS.items():
                if not INJECTOR_REQUIRES.get(inj_name, set()) <= cols:
                    continue  # not applicable on this substrate
                for p in cfg["severities"]:
                    t0 = time.time()
                    failed, meta = fn(clean, p, seed, fx=fx)
                    prof = rdm_profile(compute_all(failed, include=stats), oracle)
                    rules_fired, hits = detection_summary(validator.run(failed))
                    drift_fired, drift_share = (False, 0.0)
                    if use_drift:
                        drift_fired, drift_share = evidently_drift_fired(clean, failed)
                    detected = rules_fired or drift_fired
                    rows.append({
                        "substrate": sub_name, "seed": seed, "injector": inj_name,
                        "severity": p, "rows_affected": meta["rows_affected"],
                        **{f"rdm_{k}": v for k, v in prof.items()},
                        "max_rdm": max(prof.values()),
                        "rules_fired": rules_fired, "rule_hits": ";".join(hits),
                        "drift_fired": drift_fired, "drift_share": drift_share,
                        "detected_any": detected,
                        "silent": is_silent(prof, detected),
                        "runtime_s": round(time.time() - t0, 2),
                    })
        out = out_dir / f"grid_{sub_name}.csv"
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"[rapidbench] wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/grid.yaml")
    run(ap.parse_args().config)
