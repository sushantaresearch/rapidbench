"""E1 executor: run a generated pipeline in an isolated subprocess against a
substrate CSV, parse its JSON stats contract, and score each statistic against
the oracle with RDM. Key-independent: works on any pipeline code string,
whether hand-written references or LLM panel outputs.

Output contract (frozen in prompts/pipeline_gen_prompt.md v0.2): the pipeline
reads the CSV path from sys.argv[1] and prints exactly one JSON object as the
final stdout line with keys:
  s1_duty_by_month          {month: total duty}
  s2_chapter_duty_share     {chapter: share of total duty}
  s3_effective_duty_rate    float
  s4_uv_below_half_median_share  float
  s5_top_origin_duty_share  float
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .metrics import rdm

CONTRACT_KEYS = ["s1_duty_by_month", "s2_chapter_duty_share",
                 "s3_effective_duty_rate", "s4_uv_below_half_median_share",
                 "s5_top_origin_duty_share"]


def run_pipeline(code: str, csv_path: str, timeout_s: int = 90) -> dict:
    """Execute pipeline code in a fresh isolated interpreter. Returns
    {ok, stats, error, stdout_tail}."""
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "pipeline.py"
        f.write_text(code)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(f), csv_path],
                capture_output=True, text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return {"ok": False, "stats": None, "error": "timeout",
                    "stdout_tail": ""}
    tail = proc.stdout.strip().splitlines()[-5:] if proc.stdout.strip() else []
    if proc.returncode != 0:
        return {"ok": False, "stats": None,
                "error": f"exit {proc.returncode}: "
                         f"{proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else 'no stderr'}",
                "stdout_tail": "\n".join(tail)}
    stats = _parse_last_json(proc.stdout)
    if stats is None:
        return {"ok": False, "stats": None, "error": "no JSON contract on stdout",
                "stdout_tail": "\n".join(tail)}
    missing = [k for k in CONTRACT_KEYS if k not in stats]
    if missing:
        return {"ok": False, "stats": stats,
                "error": f"contract keys missing: {missing}",
                "stdout_tail": "\n".join(tail)}
    return {"ok": True, "stats": stats, "error": None,
            "stdout_tail": "\n".join(tail)}


def _parse_last_json(stdout: str):
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None



def _canon(v):
    """Canonicalize dict keys for scoring: '3' and '03' are the same chapter.
    JSON round-trips and pandas dtype inference de-pad numeric string keys;
    that is a formatting difference, not a defect. Only pure-digit keys of
    length <= 2 are padded, so genuinely wrong chapters (e.g. '38' derived
    from hs6 read as int) remain wrong and still score as defective."""
    if isinstance(v, dict):
        out = {}
        for k, val in v.items():
            ks = str(k)
            out[ks.zfill(2) if ks.isdigit() and len(ks) <= 2 else ks] = val
        return out
    return v

def score_pipeline(stats: dict, oracle: dict) -> dict[str, float]:
    """Per-statistic RDM of the pipeline's reported values vs the oracle.
    Execution or contract failure is scored upstream, not here."""
    return {k: rdm(_canon(stats[k]), _canon(oracle[k])) for k in CONTRACT_KEYS}


def classify(result: dict, scores: dict | None,
             material: float = 0.01) -> str:
    """E1 outcome taxonomy per pipeline sample:
    crash | contract_violation | correct | defective(list of stats)."""
    if not result["ok"]:
        return "crash" if result["error"] and "exit" in str(result["error"]) \
            else "contract_violation"
    bad = [k for k, v in scores.items() if v > material]
    return "correct" if not bad else "defective:" + ",".join(bad)
