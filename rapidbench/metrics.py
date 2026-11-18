"""Metrics: Revenue Distortion Magnitude (RDM), silent-failure rate, and
detection scoring. RDM is the benchmark's severity axis: how far each reported
revenue/compliance statistic moves from its oracle value under a failure.
"""
from __future__ import annotations


def rdm(fail, oracle) -> float:
    """Relative distortion. Scalars: |f-o|/|o|. Dict vectors: L1(f-o)/L1(o)."""
    if isinstance(oracle, dict):
        keys = set(oracle) | set(fail)
        num = sum(abs(fail.get(k, 0.0) - oracle.get(k, 0.0)) for k in keys)
        den = sum(abs(v) for v in oracle.values())
        return num / den if den else float("nan")
    if oracle == 0:
        return float("nan")
    return abs(fail - oracle) / abs(oracle)


def rdm_profile(stats_fail: dict, stats_oracle: dict) -> dict[str, float]:
    return {k: rdm(stats_fail[k], stats_oracle[k]) for k in stats_oracle}


def is_silent(profile: dict[str, float], detected: bool, threshold: float = 0.01) -> bool:
    """A failure is silent when it materially distorts at least one statistic
    (max RDM above threshold) yet no validator fires."""
    return (max(profile.values()) > threshold) and (not detected)


def detection_summary(fired: dict[str, bool]) -> tuple[bool, list[str]]:
    hits = [r for r, f in fired.items() if f]
    return (len(hits) > 0), hits
