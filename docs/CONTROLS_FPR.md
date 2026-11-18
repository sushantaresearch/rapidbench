# Clean-control false positives, seeds 42-46 (n=20000 each)

Each tier evaluated clean-vs-clean. Any firing here is a false
alarm; detection numbers in the grid are only meaningful against a
zero-FP baseline. R9 (unit-value extreme rate) was calibrated on the
clean reference precisely to hold this at zero.

|   seed | V1_rules_fired   | V1_hits   | V1b_gx_fired   | V2_drift_fired   |   V2_drift_share |
|-------:|:-----------------|:----------|:---------------|:-----------------|-----------------:|
|     42 | False            | -         | False          | False            |                0 |
|     43 | False            | -         | False          | False            |                0 |
|     44 | False            | -         | False          | False            |                0 |
|     45 | False            | -         | False          | False            |                0 |
|     46 | False            | -         | False          | False            |                0 |

FPR over 5 seeds: V1=0%, V1b=0%, V2=0%

## Public-substrate controls (2 Jul 2026)

S-C (CTGAN): rules and drift both quiet on clean-vs-clean. S-B (DATE):
drift quiet; R4_cif_fob_ratio fires on the clean frame (2.19% of clean
rows have CIF exactly equal to FOB against the fixed 2% band). See
docs/E2_CROSS_SUBSTRATE.md for the net-detection protocol this induces.
Reproduce: PYTHONPATH=. python3 scripts/controls_real.py
