# E1 harness self-test (real subprocess runs)
n=20000 synthetic declarations, seed=42. Correct pipeline must score ~0 RDM on every statistic; seeded-defect pipelines must classify as defective on exactly the statistics their bug touches. Note the mean-of-ratios case: a real bug landing under the 1% materiality threshold and passing as correct, a threshold-sensitivity finding the paper will report.

| pipeline        | ok   |   rdm_s1_% |   rdm_s2_% |   rdm_s3_% |   rdm_s4_% |   rdm_s5_% | verdict                          | error   |
|:----------------|:-----|-----------:|-----------:|-----------:|-----------:|-----------:|:---------------------------------|:--------|
| P_ref_correct   | True |          0 |      0     |      0     |          0 |          0 | correct                          | -       |
| P_bug_hs_dtype  | True |          0 |     53.942 |      0     |          0 |          0 | defective:s2_chapter_duty_share  | -       |
| P_bug_rate_agg  | True |          0 |      0     |      0.905 |          0 |          0 | correct                          | -       |
| P_bug_fob_denom | True |          0 |      0     |      7.981 |          0 |          0 | defective:s3_effective_duty_rate | -       |