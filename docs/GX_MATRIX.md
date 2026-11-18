# V1b: Great Expectations 1.18.2 suite vs injector classes

Synthetic substrate, n=20000, seed=42, severity p=0.05. Suite: hs6
6-digit regex; non-negative bounds on qty/cif/fob/duty; compound
uniqueness on (declaration_id, amendment_no). Same reference-free
posture as production GX deployments: expectations encode schema
knowledge, not a clean-reference comparison.

| Injector | regex(hs6) | between | compound_unique | any |
|---|---|---|---|---|
| CONTROL_clean | - | - | - | no |
| F01_hs_leading_zero_loss | YES | - | - | **YES** |
| F02_unit_qty_mismatch | - | - | - | no |
| F03_fx_stale_rate | - | - | - | no |
| F04_cif_fob_conflation | - | - | - | no |
| F05_tariff_year_misjoin | - | - | - | no |
| F06_outcome_leakage | - | - | - | no |
| F07_duplicate_amendments | - | - | YES | **YES** |
| F08_null_zerofill | - | YES | - | **YES** |
| F09_partner_swap | - | - | - | no |
| F10_schema_drift_fallback | - | - | - | no |
| F11_dedup_overreach | - | - | - | no |
| F12_country_code_drift | - | - | - | no |

Detected 3/12: F01_hs_leading_zero_loss, F07_duplicate_amendments, F08_null_zerofill

Missed 9/12: F02_unit_qty_mismatch, F03_fx_stale_rate, F04_cif_fob_conflation, F05_tariff_year_misjoin, F06_outcome_leakage, F09_partner_swap, F10_schema_drift_fallback, F11_dedup_overreach, F12_country_code_drift

Control fired: False (must be False; zero false alarms on clean data).
