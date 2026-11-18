"""V2 detection family: distribution-drift monitoring via Evidently.

Fires when Evidently's DataDriftPreset flags dataset-level drift between the
clean reference frame and the (possibly failed) current frame on the numeric
and categorical columns a revenue mart would monitor.
"""
from __future__ import annotations

import pandas as pd

MONITORED = ["cif_usd", "fob_usd", "qty", "duty_rate", "duty_paid_usd",
             "chapter", "origin_iso3", "currency"]


def _subset(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in MONITORED if c in df.columns]
    return df[cols]


def evidently_drift_fired(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[bool, float]:
    """Return (dataset_drift_flag, share_of_drifted_columns)."""
    ref, cur = _subset(reference), _subset(current)
    try:  # evidently >= 0.7 API
        from evidently import Report
        from evidently.presets import DataDriftPreset
        rep = Report([DataDriftPreset()])
        snapshot = rep.run(reference_data=ref, current_data=cur)
        d = snapshot.dict()
        share, flag = _extract_from_dict(d)
        return flag, share
    except ImportError:
        pass
    # evidently 0.4--0.6 API
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset
    rep = Report(metrics=[DataDriftPreset()])
    rep.run(reference_data=ref, current_data=cur)
    d = rep.as_dict()
    share, flag = _extract_from_dict(d)
    return flag, share


def _extract_from_dict(d: dict) -> tuple[float, bool]:
    """Evidently >=0.7: read DriftedColumnsCount observed value (not config).
    Fires when at least one monitored column drifts past its own threshold."""
    for m in d.get("metrics", []):
        cfg = m.get("config", {})
        if str(cfg.get("type", "")).endswith("DriftedColumnsCount"):
            val = m.get("value", {})
            share = float(val.get("share", 0.0))
            count = float(val.get("count", 0.0))
            return share, count > 0
    # Legacy (<=0.6) payloads: look for dataset_drift boolean.
    share, flag = 0.0, False

    def walk(x):
        nonlocal share, flag
        if isinstance(x, dict):
            for k, v in x.items():
                lk = str(k).lower()
                if lk == "share_of_drifted_columns" and isinstance(v, (int, float)):
                    share = float(v)
                if lk == "dataset_drift" and isinstance(v, bool):
                    flag = flag or v
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(d)
    return share, flag
