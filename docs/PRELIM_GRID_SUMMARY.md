# Preliminary grid summary (S-A synthetic, real run, 2 Jul 2026)
Cells: 180 (12 classes x 3 severities x 5 seeds). Silent cells: 19.

| injector                  |   ('detected_any', 0.01) |   ('detected_any', 0.05) |   ('detected_any', 0.2) |   ('max_rdm', 0.01) |   ('max_rdm', 0.05) |   ('max_rdm', 0.2) |   ('silent', 0.01) |   ('silent', 0.05) |   ('silent', 0.2) |
|:--------------------------|-------------------------:|-------------------------:|------------------------:|--------------------:|--------------------:|-------------------:|-------------------:|-------------------:|------------------:|
| F01_hs_leading_zero_loss  |                        1 |                        1 |                       1 |               0.54  |               0.54  |              0.54  |                0   |                0   |                 0 |
| F02_unit_qty_mismatch     |                        1 |                        1 |                       1 |               0.006 |               0.031 |              0.132 |                0   |                0   |                 0 |
| F03_fx_stale_rate         |                        0 |                        0 |                       0 |               0     |               0     |              0.001 |                0   |                0   |                 0 |
| F04_cif_fob_conflation    |                        0 |                        1 |                       1 |               0.001 |               0.004 |              0.014 |                0   |                0   |                 0 |
| F05_tariff_year_misjoin   |                        1 |                        1 |                       1 |               0.158 |               0.158 |              0.158 |                0   |                0   |                 0 |
| F06_outcome_leakage       |                        0 |                        0 |                       0 |               0.003 |               0.016 |              0.067 |                0   |                1   |                 1 |
| F07_duplicate_amendments  |                        1 |                        1 |                       1 |               0.015 |               0.048 |              0.195 |                0   |                0   |                 0 |
| F08_null_zerofill         |                        1 |                        1 |                       1 |               0.016 |               0.048 |              0.195 |                0   |                0   |                 0 |
| F09_partner_swap          |                        0 |                        0 |                       0 |               0.011 |               0.014 |              0.02  |                0.2 |                0.6 |                 1 |
| F10_schema_drift_fallback |                        1 |                        1 |                       1 |               0.074 |               0.074 |              0.074 |                0   |                0   |                 0 |
| F11_dedup_overreach       |                        1 |                        1 |                       1 |               0.016 |               0.016 |              0.016 |                0   |                0   |                 0 |
| F12_country_code_drift    |                        1 |                        1 |                       1 |               0.016 |               0.041 |              0.201 |                0   |                0   |                 0 |

Detection = V1 rules OR V2 Evidently drift. Silent = max RDM > 1% and undetected.
Scaffold verification on the synthetic substrate only; not paper results.