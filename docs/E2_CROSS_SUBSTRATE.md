# E2 cross-substrate replication (S-B DATE, S-C CTGAN)

Run: 2 Jul 2026, configs/grid_real.yaml (seeds 42-46, severities 0.01/0.05/0.20,
V1 rules + V2 drift). Outputs: results/grid_date.csv (150 rows),
results/grid_ctgan.csv (120 rows), results/controls_real.csv,
results/grid_date_net.csv, results/cross_substrate_status.json.

## Substrates

- S-B: DATE public synthetic customs imports, 100,000 declarations, 2013,
  12 months, 91 chapters, 1,721 hs6 values, 1,525 rows in chapters 01-09
  (leading-zero exposure real). duty_rate is the per-row effective rate
  total.taxes/cif.value. sha256/16 e89c97727f2193f3.
- S-C: CTGAN-generated Korea customs declarations (arXiv:2208.02484),
  54,000 rows, 506 dropped non-positive mass/price, 53,494 used, 18 months,
  2,481 hs6. Native ad-valorem Tax Rate. sha256/16 cb6984e165994f7c.

Applicability by column requirements: S-B lacks currency (F03 n/a) and an
ex-ante risk flag (F06, S6 n/a): 10 classes, 150 cells. S-C additionally
lacks FOB (F04, F10 n/a): 8 classes, 120 cells.

## Clean controls (results/controls_real.csv)

- S-C: no rule fires, no drift fires on clean-vs-clean.
- S-B: drift quiet; R4_cif_fob_ratio FIRES ON CLEAN DATA. R4 is the one
  fixed-band check in the suite (median CIF/FOB in [1.02, 1.30]; at most 2%
  of rows at ratio <= 1.0). Clean DATE has 2.19% of rows with CIF exactly
  equal to FOB, 0.19pp over the band. The rule is a permanent alarm on this
  substrate and carries no detection information there.

Protocol: detection on a substrate is scored net of rules that fire on that
substrate's clean control (V1_net union V2). S-A and S-C have empty
clean-firing sets, so raw equals net; on S-B only R4 is excluded.
The validator source is frozen as reviewed; the miscalibration is reported
as a finding, not repaired post hoc (same policy as tasks.py zfill).

## Results

S-B net: 26/150 cells silent. S-C: 9/120. With S-A's 19/180, the pooled
grid is 54/450 (12.0%) silent.

Per-class status (D detected every cell; d detected except immaterial
escapes; S silent, never detected while material; i never detected, never
material; -- n/a):

| Class | S-A | S-B | S-C |
|---|---|---|---|
| F01 hs leading-zero loss | D | D | D |
| F02 unit-qty mismatch | D | D | D |
| F03 stale FX rate | i | -- | -- |
| F04 CIF/FOB conflation | d | S | -- |
| F05 tariff-year misjoin | D | D | D |
| F06 outcome leakage | S | -- | -- |
| F07 duplicate amendments | D | D | D |
| F08 null zero-fill | D | D | D |
| F09 partner swap | S | S | S |
| F10 schema-drift fallback | D | S | -- |
| F11 dedup overreach | D | D | i |
| F12 country-code drift | D | D | D |

## Findings

1. Miscalibrated-rule masking (S-B). F10 (CIF column silently replaced by
   FOB) distorts statistics by 20.2% and is silent in all 15 S-B cells;
   F04 is silent in 7 (max 4.2%). The only check that encodes their
   signature is R4, and R4 cannot stay quiet on clean DATE, so its alarm is
   indistinguishable from background. On S-A the same rule is quiet on
   clean data and catches both classes. A fault class is masked exactly
   when its dedicated detector false-alarms at baseline.
2. F09 is silent on every substrate: max RDM 4.0% (S-A), 2.6% (S-B),
   8.4% (S-C). Origin permutation preserves every marginal the rules and
   the drift monitor test; the blind spot is relationship-level and
   substrate-invariant.
3. Rule attribution is class-specific everywhere else: F01->R1, F02->R9
   (+drift), F05->R5+R7, F07->R3+R6, F08->R2+R3+R9, F11->R6+R7, F12->R8
   (+drift at 0.05/0.20).
4. F11 on S-C is undetected but immaterial (max RDM 0.4%): the CTGAN table
   has almost no same-importer/hs6/month multiplicity to over-deduplicate.
5. F05 magnitude caveat. On substrates where duty_rate is a derived
   per-row effective rate (S-B) or a native per-row rate (S-C), the
   chapter-vintage swap collapses within-chapter rate variation, so RDM
   magnitudes (up to 510% on S-B) read as rate-collapse, not a pure
   vintage shift. Detection status is unaffected (R5+R7 fire).
6. Severity-invariant classes (F05, F10, F11 ignore p by design) show
   identical RDM across severities within a seed, as expected.

## Scope

E1 (generation panel) and E3 (review panel), and the V1b GX suite, are
evaluated on S-A only; V1/V2 run on all three substrates. F03 and F06 are
untestable on the public substrates because released data carry no currency
column and no ex-ante risk flag; the joins those classes corrupt live
upstream of published marts.
