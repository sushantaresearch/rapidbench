"""Mock-panel end-to-end tests: the real driver, extraction, subprocess
execution, scoring, and every verdict branch, with zero network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rapidbench.panel import MockClient, extract_code, run_panel, _MOCK_REPLIES


def test_extract_code_takes_last_fence_and_strips_prose():
    reply = "chatter\n```python\nprint(1)\n```\nmore\n```python\nprint(2)\n```\nbye"
    assert extract_code(reply) == "print(2)"
    assert extract_code("no fence at all") == "no fence at all"


def test_mock_panel_end_to_end(tmp_path):
    df = run_panel(list(_MOCK_REPLIES), k=1, client_cls=MockClient,
                   out_prefix="e1_test", n_rows=4000,
                   results_dir=tmp_path)
    v = dict(zip(df["model"], df["verdict"]))
    assert v["mock/correct"] == "correct"
    assert v["mock/bug-hs-dtype"].startswith("defective:") and "s2" in v["mock/bug-hs-dtype"]
    # Documented threshold-sensitivity case (docs/E1_SELFTEST.md): the
    # mean-of-ratios defect distorts s3 by ~0.9%, UNDER the 1% materiality
    # gate, so it must classify as correct while showing nonzero s3 RDM.
    rate_row = df[df["model"] == "mock/bug-rate-agg"].iloc[0]
    assert rate_row["verdict"] == "correct"
    assert 0.0 < rate_row["rdm_s3"] < 0.01
    assert v["mock/contract-violation"] == "contract_violation"
    # key-canonicalization regression: chapter-column pipeline is substantively
    # correct ('3' vs '03' is formatting); the hs6-as-int trap must STAY defective.
    assert v["mock/chapter-col-correct"] == "correct"
    assert v["mock/crash"] == "crash"
    assert (tmp_path / "e1_test_results.csv").exists()
    assert (tmp_path / "e1_test_manifest.json").exists()
    saved = list((tmp_path / "e1_test_pipelines").rglob("sample_0.py"))
    assert len(saved) == len(_MOCK_REPLIES)


def test_truncated_fence_is_stripped_and_crashes(tmp_path):
    """A completion cut off before the closing fence must not execute the
    fence marker itself; the unterminated code still verdicts crash."""
    from rapidbench.panel import run_panel, MockClient
    df = run_panel(["mock/truncated-fence"], k=1, client_cls=MockClient,
                   out_prefix="tfence", results_dir=tmp_path)
    assert df.iloc[0]["verdict"] == "crash"
    assert df.iloc[0]["finish_reason"] == "length"
    saved = (tmp_path / "tfence_pipelines" / "mock_truncated-fence"
             / "sample_0.py").read_text()
    assert "```" not in saved


def test_e3_mock_driver(tmp_path, monkeypatch):
    """E3 driver end to end offline: 13 frames x model, clean control not
    counted as class match, F06 mock reply matched, results CSV written."""
    import subprocess, sys, pandas as pd
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "scripts/e3_v3_panel.py", "--mock",
         "--models", "mock/x", "--out", "e3_test"],
        cwd=repo, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    df = pd.read_csv(repo / "results" / "e3_test_results.csv")
    assert len(df) == 13
    clean = df[df.fault == "F00_clean"].iloc[0]
    assert not clean["flagged"] and not clean["class_match"]
    f06 = df[df.fault == "F06_outcome_leakage"].iloc[0]
    assert f06["flagged"] and f06["class_match"]
    low_only = df[df.fault == "F01_hs_leading_zero_loss"].iloc[0]
    assert not low_only["flagged"]


def test_e3_resume_reruns_only_errors(tmp_path):
    """--resume keeps clean rows and re-runs only errored (model,fault)."""
    import subprocess, sys, pandas as pd
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "scripts/e3_v3_panel.py", "--mock",
                    "--models", "mock/x", "--out", "e3_res"],
                   cwd=repo, capture_output=True, text=True, timeout=300,
                   check=True)
    p = repo / "results" / "e3_res_results.csv"
    df = pd.read_csv(p)
    df["error"] = df["error"].astype("object")
    df.loc[df.fault.isin(["F11_dedup_overreach", "F12_country_code_drift"]),
           "error"] = "RuntimeError: HTTP 402"
    df.to_csv(p, index=False)
    r = subprocess.run([sys.executable, "scripts/e3_v3_panel.py", "--mock",
                        "--models", "mock/x", "--out", "e3_res", "--resume"],
                       cwd=repo, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "keeping 11 completed rows, re-running 2" in r.stdout
    out = pd.read_csv(p)
    assert len(out) == 13
    assert (out["error"].fillna("") == "").all()
