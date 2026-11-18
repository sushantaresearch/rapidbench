# RAPID-Bench smoke test (real run)
n=20000 synthetic declarations, p=0.05, seed=42, runtime 13.1s, pandas 3.0.2.
False positives on clean data: rules=none; evidently control fired=False.

| injector                  |   rows_affected |   max_RDM_% | worst_stat          |   S1_duty_% | rules   | drift   | rules_fired                                                 | SILENT   |
|:--------------------------|----------------:|------------:|:--------------------|------------:|:--------|:--------|:------------------------------------------------------------|:---------|
| F01_hs_leading_zero_loss  |            5064 |       53.94 | S2_duty_by_chapter  |        0    | True    | False   | R1_hs_format,R5_tariff_join_coverage,R7_chapter_share_drift | False    |
| F02_unit_qty_mismatch     |            1000 |        3.77 | S4_uv_screen_rate   |        0    | True    | True    | R9_unit_value_bounds                                        | False    |
| F03_fx_stale_rate         |             451 |        0.03 | S4_uv_screen_rate   |        0    | False   | False   | -                                                           | False    |
| F04_cif_fob_conflation    |            1000 |        0.35 | S1_total_duty       |        0.35 | True    | False   | R4_cif_fob_ratio                                            | False    |
| F05_tariff_year_misjoin   |           20000 |       15.19 | S2_duty_by_chapter  |        1.39 | True    | False   | R5_tariff_join_coverage,R7_chapter_share_drift              | False    |
| F06_outcome_leakage       |            1000 |        1.64 | S6_flag_precision   |        0    | False   | False   | -                                                           | True     |
| F07_duplicate_amendments  |            1000 |        4.91 | S1_total_duty       |        4.91 | True    | False   | R3_duplicate_keys,R6_row_reconciliation                     | False    |
| F08_null_zerofill         |            1000 |        4.91 | S2_duty_by_chapter  |        4.91 | True    | False   | R2_positive_value,R4_cif_fob_ratio,R9_unit_value_bounds     | False    |
| F09_partner_swap          |            1000 |        2.46 | S5_top_origin_share |        0    | False   | False   | -                                                           | True     |
| F10_schema_drift_fallback |           20000 |        7.37 | S2_duty_by_chapter  |        7.37 | True    | False   | R4_cif_fob_ratio                                            | False    |
| F11_dedup_overreach       |             341 |        1.82 | S2_duty_by_chapter  |        1.82 | True    | False   | R6_row_reconciliation                                       | False    |
| F12_country_code_drift    |            1000 |        4.71 | S5_top_origin_share |        0    | True    | True    | R8_iso3_vocabulary                                          | False    |

Silent = max RDM > 1% with neither rule nor drift tier firing. Scaffold verification only; not paper results.