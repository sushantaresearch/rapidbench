# E3 adjudication: protocol and evidence

Raw material: 65 reviewer replies (5 models x 13 frames) under
`results/e3_reviews/`, scored automatically into `results/e3_results.csv`
by a conservative keyword map (`docs/SCORING_KEYS.md`). This document
records the manual audit of all 65 replies and every cell whose
`class_match` value was changed. Final labels live in
`results/e3_adjudicated.csv` (`identified`, `adjudication_note`).

## Protocol (fixed before reading any reply)

A cell counts as **identified** when the reply names the injected
mechanism or a direct observable consequence of it, in any wording,
tied to the correct column(s). Generic distribution-drift remarks on a
touched column do not qualify; neither do observations about the
pipeline source or the experimental design. **Flagged** (any
medium/high severity failure raised) is tracked separately, so a
reviewer can be flagged-without-identifying and, at low stated
severity, identified-without-flagging.

Ground truth per class was read from `rapidbench/injectors.py` before
opening the replies. Two consequences were pre-registered:

- **F09 partner swap** permutes `origin_iso3` values within the
  selected rows, so the column's marginal profile (counts, top-5,
  cardinality) is exactly unchanged. The fault is information-
  theoretically invisible to profile-based review; a zero score here
  measures the information set, not the models.
- **F06 outcome leakage** leaves a single marginal trace: the
  `risk_flag` mean moves 0.3734 to 0.3710 (0.24 pp). "Flag rate
  moved" alone therefore does not identify leakage; a match requires
  naming the flag-outcome relationship (leakage, label contamination,
  flag copied from outcome).

## Overrides (6 upgrades, 1 downgrade)

| Cell | Change | Verbatim evidence (from the raw reply) |
|---|---|---|
| Claude / F10 | no-match -> identified | "Current batch cif_usd statistics (mean=16796.84, median=8950.13, max=750524.11) exactly match reference fob_usd ... CIF should exceed FOB due to insurance and freight costs." Exact mechanism; the F10 keyword list (schema/rename/fallback terms) missed it. |
| GPT-4o / F08 | no-match -> identified | "The minimum value of cif_usd in the current batch is 0.0, which is not possible for a valid transaction." Mechanism named; keyword list required the literal word "zero". |
| Llama / F01 | no-match -> identified | "Top 5 HS6 codes in the current batch do not match the reference window (e.g., '014388' vs '14388')". The cited pair is the de-padded code itself: the mechanism made visible. |
| Llama / F07 | no-match -> identified | "The number of unique values for 'decl_id' in the current batch (21000) exceeds the number of unique values in the reference window (20000)". Direct consequence of amendment ingestion. |
| Llama / F08 | no-match -> identified | "Minimum value of cif_usd is 0.0, which is less than the minimum value in the reference window (137.420239)". |
| DeepSeek / F08 | no-match -> identified | "min value is 0.0, which is lower than the reference window's min of 137.420239". |
| Gemini / F04 | match -> no-match | "The statistical profiles of numerous columns ... are exact matches. This indicates the batch is not new data but a copy of old data with minor modifications to cif_usd and duty_paid_usd." The reply detects the same-frame injection design, not the CIF/FOB conflation; the keyword list credited it because the evidence string contains "cif". Remains **flagged**. |

All other 58 cells: keyword label confirmed by inspection. Notable
confirmations: Claude / F04 identified via "cif_usd decreased by 0.35%
while fob_usd remained identical, suggesting potential systematic
underreporting of freight/insurance costs"; Gemini / F07 identified via
"only 20,000 unique values for 21,000 rows. This introduction of
duplicate values ..."; Llama / F05 identified at stated severity "low"
(flagged=False, identified=True; the run used severity 0.05).
Gemini / F11 stays no-match: its stated evidence compares top-5
`chapter` values with top-5 `hs6` prefixes, which need not align even
in clean data, and it does not mention the visible row-count drop
(19,659 vs 20,000) that Claude cited.

## Adjudicated matrix (identified / flagged-only / silent)

| Fault | Claude | Gemini | Llama | GPT-4o | DeepSeek | n id. |
|---|---|---|---|---|---|---|
| F01 | id | id | id | id | - | 4 |
| F02 | id | id | id | id | id | 5 |
| F03 | flag* | - | - | - | - | 0 |
| F04 | id | flag* | - | - | - | 1 |
| F05 | id | id | id | - | - | 3 |
| F06 | flag* | - | - | - | - | 0 |
| F07 | id | id | id | - | - | 3 |
| F08 | id | id | id | id | id | 5 |
| F09 | - | - | - | - | - | 0 |
| F10 | id | id | - | - | - | 2 |
| F11 | id | flag* | flag | - | - | 1 |
| F12 | id | id | id | - | - | 3 |

Totals identified/12: Claude 9, Gemini 7, Llama 6, GPT-4o 3,
DeepSeek 2. Panel union: 9/12 classes. Clean control F00: 0/5 false
positives. Keyword map scored 22 identified cells; adjudication yields
27 (net +5), i.e., the automatic map is conservative and all
directional errors it made understated the panel.

## Emergent findings

**The zfill(1) pipeline audit (cells marked flag* for Claude).**
`rapidbench/tasks.py` line 15 derives chapters via
`hs6.astype(str).str.zfill(1).str[:2]`. `zfill(1)` never pads (every
string has length >= 1), so the expression is functionally `hs6[:2]`:
correct on the zero-padded clean substrate and format-naive under F01,
which is the intended, realistic premise. Claude flagged this
construction in five separate reviews (F01, F03, F04, F06, F07, F11)
as a probable `zfill(6)` typo, reasoning correctly about its failure
mode under de-padded input. This is accurate *pipeline* review, and on
F01 it correctly connects the latent weakness to the observed data
fault. On frames where the zfill remark was the only failure raised
(F03, F06), the cell is flagged-without-identifying: the reviewer
audited the code, not the injected data fault. The source file is
frozen as reviewed; it was not edited after the experiment. Gemini
raised the same construction once (F07) with a hypothetical
empty-string argument.

**Same-frame injection is detectable (Gemini / F04).** Each faulted
frame is the reference frame with the injection applied, so profiles of
untouched columns are identical between reference and current batch, a
signature no genuinely new batch would show. Gemini exploited this
exactly once. Design implication for future versions: draw the current
batch from a fresh generator seed before injecting. Disclosed as a
limitation in the paper.

**Generation and review are different competences.** DeepSeek produced
3/3 correct pipelines in E1 yet identified only 2/12 faults in E3;
GPT-4o likewise 3/3 in E1 and 3/12 in E3. Reviewer choice for
data-quality gating cannot be inferred from code-generation quality.
