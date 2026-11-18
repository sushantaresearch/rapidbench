# RAPID-Bench

Revenue-Analytics Pipeline Injected-Defect Benchmark: measuring which
data-quality failures in AI-generated customs/trade revenue pipelines are
caught by the standard DQ stack, and which silently distort the statistics
governments act on.

Code: Sushanta Paul. Paper: S. Paul, S. Chowdhury, and A. Das, ICCIT 2026.
See docs/BENCHMARK_SPEC.md for the full design,
docs/SMOKE_RESULTS.md and docs/PRELIM_GRID_SUMMARY.md for real scaffold runs.

## Quick start
    pip install -r requirements.txt
    python3 scripts/smoke_test.py            # 12 classes, rules + drift tiers
    python3 -m rapidbench.runner --config configs/grid.yaml

## Layout
    rapidbench/substrate.py   substrates (synthetic generator + local loaders)
    rapidbench/injectors.py   12 failure classes (F01--F12)
    rapidbench/tasks.py       oracle revenue/compliance statistics (S1--S6)
    rapidbench/metrics.py     RDM, silent-failure logic
    rapidbench/validators/    V1 rules, V1b GX (tested, 12-class matrix), V2 Evidently,
                              V3 LLM reviewer (scaffold, env-var key)
    rapidbench/runner.py      full experiment grid -> results/*.csv
    prompts/                  frozen E1 pipeline-generation prompt
    configs/grid.yaml         paper grid configuration

## Status honesty
Implemented and smoke-tested in-sandbox: substrate generator, all 12
injectors, oracle statistics, RDM/SFR metrics, V1 rules, V2 Evidently 0.7.21,
grid runner, E1 executor harness (subprocess isolation, contract parsing, oracle diff; self-test 4 pipelines), tests (4/4 passing). Scaffold only, run locally before trusting:
V3 OpenRouter reviewer (mock-tested driver in panel.py), real-substrate
loaders (need local file paths). No API keys anywhere in this repo.

## Status (v0.3, 2 Jul 2026)
Tested on real runs: injectors 12/12, E2 grid 180 cells
(results/grid_synthetic.csv), V1 rules, V1b Great Expectations 1.18.2
(results/gx_matrix.csv: 3/12 detected, control clean), V2 Evidently 0.7.21,
clean-control FPR 0% over seeds 42-46 (results/controls_fpr.csv), E1
executor + mock panel end-to-end (results/e1_mock_*, all five verdict
branches), figures (figs/), 6 pytest tests green.
Scaffold only (needs SP inputs): real E1 panel and V3 reviewer
(OPENROUTER_API_KEY env var; verify model IDs in configs/panel.yaml),
DATE/CTGAN substrate loaders (local file paths).
Paper skeleton: paper/rapidbench_iccit.tex (compile in Overleaf; not
compiled here).


## Release v1.7 (ICCIT 2026 camera-ready)
Replication archive for: S. Paul, S. Chowdhury, and A. Das, "Silent Data-Quality
Failures in AI-Generated Revenue-Analytics Pipelines: An Error-Injection
Benchmark," IEEE ICCIT 2026 (accepted).

Same code and results as v1.6, with these changes:
- data/: the two public substrate files are not redistributed. Run
  `bash data/fetch_substrates.sh`; it downloads them and checks SHA-256
  against data/SHA256SUMS (provenance in data/PROVENANCE.md).
- results/e1_selftest_thresholds.csv: E1 self-test verdicts at the 0.5% and
  1% materiality gates (scripts/camera_ready/e1_thresholds.py).
- figs/camera_ready/: figures as printed in the camera-ready paper (in-figure
  titles removed; Fig. 1 on a greyscale-safe scale).
- scripts/camera_ready/: scripts behind the numbers added in the camera-ready
  (per-substrate silent rates and CIs, raw vs net counts, threshold
  sensitivity, the RDM/2 share-mass check, and the figures). Each takes paths
  as arguments; see the docstring at the top of each file.
- The manuscript itself is not included.

All substrates are synthetic: the seeded generator (S-A) and two public
synthetic releases (S-B DATE, S-C CTGAN Korea). No confidential or
administrative data are used.

Licences: code under MIT (LICENSE); results, docs and figures under
CC BY 4.0 (LICENSE-DATA.md).
