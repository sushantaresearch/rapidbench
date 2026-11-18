"""E3 driver: V3 LLM-reviewer panel over the injected fault grid.

For each frame (clean control + 12 faults at one severity, one seed) each
panel model receives the reference pipeline source, the schema, and two
deterministic profiles (clean reference vs current batch), and returns a
structured failure judgment. Scoring records, per (model, frame):

  flagged      any failure with severity medium/high
  class_match  any returned failure whose class+evidence text matches the
               injected class's keyword set (conservative substring match,
               map documented below and in the artifact)

The clean control row measures the reviewer false-positive rate. Raw JSON
replies are saved per call for audit. Reviewers never see raw rows, oracle
statistics, or fault labels.

Usage:
  python scripts/e3_v3_panel.py            # real panel (needs OPENROUTER_API_KEY)
  python scripts/e3_v3_panel.py --mock     # offline harness test
  python scripts/e3_v3_panel.py --models openai/gpt-4o deepseek/deepseek-chat
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rapidbench import tasks                              # noqa: E402
from rapidbench.injectors import INJECTORS                # noqa: E402
from rapidbench.panel import OpenRouterClient             # noqa: E402
from rapidbench.substrate import generate_synthetic_declarations  # noqa: E402
from rapidbench.validators.llm_reviewer import (          # noqa: E402
    PANEL, SYSTEM, build_user_prompt, parse_review)

SEVERITY = 0.05
SEED = 42
N_ROWS = 20000

# Conservative keyword map: a returned failure counts as identifying the
# injected class only if its class+evidence text contains one of these
# substrings (case-insensitive). Documented in the artifact.
KEYWORDS = {
    "F01_hs_leading_zero_loss": ["leading zero", "zero-pad", "hs code format",
                                 "hs6 format", "5-digit", "five-digit",
                                 "truncat"],
    "F02_unit_qty_mismatch": ["unit", "quantity", "qty"],
    "F03_fx_stale_rate": ["exchange rate", "fx", "currency conversion",
                          "stale rate"],
    "F04_cif_fob_conflation": ["cif", "fob"],
    "F05_tariff_year_misjoin": ["tariff year", "duty rate", "wrong year",
                                "misjoin", "rate schedule"],
    "F06_outcome_leakage": ["leak", "outcome", "label", "target",
                            "post-clearance", "risk_flag matches",
                            "flag equals"],
    "F07_duplicate_amendments": ["duplicate", "amendment", "double count"],
    "F08_null_zerofill": ["zero", "null", "missing", "imput"],
    "F09_partner_swap": ["origin", "partner", "country swap", "iso"],
    "F10_schema_drift_fallback": ["schema", "column", "renam", "fallback"],
    "F11_dedup_overreach": ["dedup", "dropped", "removed rows",
                            "row count", "fewer rows"],
    "F12_country_code_drift": ["country code", "iso", "code drift",
                               "unknown code", "invalid code"],
}


def profile(df: pd.DataFrame) -> str:
    """Deterministic generic profile: the same fields any off-the-shelf
    profiler emits, identical posture for reference and current."""
    out = {"rows": int(len(df)), "columns": {}}
    for c in df.columns:
        s = df[c]
        col = {"dtype": str(s.dtype), "nulls": int(s.isna().sum()),
               "unique": int(s.nunique(dropna=True))}
        if pd.api.types.is_numeric_dtype(s):
            col.update({k: (None if pd.isna(v) else round(float(v), 6))
                        for k, v in {
                            "mean": s.mean(), "std": s.std(),
                            "min": s.min(), "median": s.median(),
                            "max": s.max()}.items()})
        else:
            top = s.astype(str).value_counts().head(5)
            col["top5"] = {str(k): int(v) for k, v in top.items()}
        out["columns"][c] = col
    return json.dumps(out, sort_keys=True)


def pipeline_source() -> str:
    fns = [tasks.s1_total_duty, tasks.s2_duty_by_chapter,
           tasks.s3_effective_duty_rate, tasks.s4_undervaluation_screen_rate,
           tasks.s5_top_origin_duty_share, tasks.s6_flag_precision]
    return "\n\n".join(inspect.getsource(f) for f in fns)


def score(review: dict, fault: str) -> tuple[bool, bool, str]:
    fails = review.get("failures", [])
    flagged = any(str(f.get("severity", "")).lower() in ("medium", "high")
                  for f in fails)
    if fault == "F00_clean":
        return flagged, False, ""
    kws = KEYWORDS[fault]
    for f in fails:
        text = (str(f.get("class", "")) + " " + str(f.get("evidence", ""))).lower()
        for kw in kws:
            if kw in text:
                return flagged, True, str(f.get("class", ""))[:60]
    return flagged, False, ""


class MockReviewer:
    """Offline reviewer exercising every scoring branch."""

    def __init__(self, model: str, temperature: float = 0.0):
        self.model = model

    @property
    def name(self) -> str:
        return self.model

    def generate(self, prompt: str, system: str | None = None) -> str:
        assert system, "system prompt must be passed"
        if "F06" in getattr(self, "_fault", ""):
            return json.dumps({"failures": [
                {"class": "label leakage",
                 "evidence": "risk_flag agreement with outcome shifted \u2192 leak",
                 "severity": "high"}]})
        if "F00" in getattr(self, "_fault", ""):
            return json.dumps({"failures": []})
        return "```json\n" + json.dumps({"failures": [
            {"class": "unspecified anomaly", "evidence": "profile delta",
             "severity": "low"}]}) + "\n```"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--models", nargs="*", default=None)
    ap.add_argument("--severity", type=float, default=SEVERITY)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=None)
    ap.add_argument("--resume", action="store_true",
                    help="keep completed rows in <out>_results.csv and "
                         "re-run only rows that recorded an error")
    args = ap.parse_args()

    models = args.models or PANEL
    prefix = args.out or ("e3_mock" if args.mock else "e3")
    client_cls = MockReviewer if args.mock else OpenRouterClient

    results_dir = Path("results")
    raw_dir = results_dir / f"{prefix}_reviews"
    raw_dir.mkdir(parents=True, exist_ok=True)

    clean, fx = generate_synthetic_declarations(n=N_ROWS, seed=args.seed)
    ref_prof = profile(clean)
    src = pipeline_source()
    schema = ", ".join(f"{c}:{clean[c].dtype}" for c in clean.columns)
    user_sha = hashlib.sha256(
        (SYSTEM + src + schema).encode()).hexdigest()[:16]

    frames = [("F00_clean", clean)]
    for name, fn in INJECTORS.items():
        inj, _meta = fn(clean, p=args.severity, seed=args.seed, fx=fx)
        frames.append((name, inj))

    rows = []
    done_pairs: set[tuple[str, str]] = set()
    prev_path = results_dir / f"{prefix}_results.csv"
    if args.resume and prev_path.exists():
        prev = pd.read_csv(prev_path)
        keep = prev[prev["error"].astype("object").fillna("") == ""]
        rows = keep.to_dict("records")
        done_pairs = {(r["model"], r["fault"]) for r in rows}
        print(f"resume: keeping {len(rows)} completed rows, "
              f"re-running {len(frames) * len(models) - len(rows)}")
    total = len(frames) * len(models) - len(done_pairs)
    done = 0
    for fault, frame in frames:
        cur_prof = profile(frame)
        user = build_user_prompt(src, schema, ref_prof, cur_prof)
        for model in models:
            if (model, fault) in done_pairs:
                continue
            client = client_cls(model, temperature=0.0)
            client._fault = fault  # mock only; ignored by real client
            done += 1
            t0 = time.time()
            err = ""
            flagged = match = False
            mclass = ""
            nfail = -1
            try:
                reply = client.generate(user, system=SYSTEM)
                mdir = raw_dir / model.replace("/", "_")
                mdir.mkdir(exist_ok=True)
                (mdir / f"{fault}.txt").write_text(reply, encoding="utf-8")
                review = parse_review(reply)
                nfail = len(review["failures"])
                flagged, match, mclass = score(review, fault)
            except Exception as e:  # noqa: BLE001 - recorded, not fatal
                err = f"{type(e).__name__}: {e}"[:200]
            rt = round(time.time() - t0, 2)
            print(f"[{done}/{total}] {fault:28s} {model:38s} "
                  f"flagged={flagged} match={match} {rt}s {err}",
                  flush=True)
            rows.append({"model": model, "fault": fault,
                         "severity": args.severity if fault != "F00_clean"
                         else 0.0,
                         "n_failures": nfail, "flagged": flagged,
                         "class_match": match, "matched_class": mclass,
                         "runtime_s": rt, "error": err})

    order = {f: i for i, f in enumerate([n for n, _ in frames])}
    df = pd.DataFrame(rows).sort_values(
        ["fault", "model"], key=lambda c: c.map(order) if c.name == "fault"
        else c).reset_index(drop=True)
    df.to_csv(results_dir / f"{prefix}_results.csv", index=False)
    manifest = {
        "experiment": "E3", "mode": prefix,
        "client": client_cls.__name__, "models": models,
        "severity": args.severity, "seed": args.seed,
        "temperature": 0.0, "prompt_sha256_16": user_sha,
        "substrate": {"kind": "synthetic", "n": N_ROWS, "seed": args.seed},
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (results_dir / f"{prefix}_manifest.json").write_text(
        json.dumps(manifest, indent=2))

    piv = df[df.fault != "F00_clean"].pivot_table(
        index="fault", columns="model", values="class_match",
        aggfunc="first")
    print("\nclass_match by fault x model:")
    print(piv.to_string())
    fpr = df[df.fault == "F00_clean"][["model", "flagged"]]
    print("\nclean-control flagged (false positive):")
    print(fpr.to_string(index=False))


if __name__ == "__main__":
    main()
