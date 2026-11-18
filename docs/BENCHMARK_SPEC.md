# RAPID-Bench: Benchmark Specification v0.1

**Working title:** Silent Data-Quality Failures in AI-Generated Revenue-Analytics
Pipelines: An Error-Injection Benchmark

**Author:** Sushanta Paul (sole author). ORCID 0009-0007-8071-6971.
**Status:** design frozen for ICCIT 2026 sprint; journal extension planned.
**Date:** 2 July 2026.

## 1. Thesis

Generative AI accelerates the construction of revenue-analytics pipelines
(duty aggregation, valuation screening, mirror-gap estimation), but some
failure classes those pipelines introduce are invisible to the standard
data-quality stack (rule suites, drift monitors) while materially distorting
the revenue statistics governments act on. RAPID-Bench measures which classes
are caught, by which detection tier, at what severity, and at what revenue
cost, on customs/trade substrates.

## 2. Contributions

1. A 12-class failure taxonomy for revenue-analytics pipelines, six classes
   domain-specific to customs/trade (HS leading-zero loss, unit-quantity
   mismatch, stale-FX conversion, CIF/FOB conflation, tariff-vintage misjoin,
   post-clearance outcome leakage) and six generic classes instantiated on
   revenue data.
2. Revenue Distortion Magnitude (RDM): a severity metric that scores each
   failure by the relative distortion of six revenue/compliance statistics
   (total duty, chapter shares, effective duty rate, undervaluation-screen
   rate, top-origin share, risk-flag precision), extending the duty-weighted
   evaluation philosophy of the author's HS-classification work from model
   outputs to pipeline outputs.
3. A four-tier detection matrix evaluated on the same injected grid:
   V1 rule suites (nine reference rules; GX re-expression), V2 distribution
   drift (Evidently), V3 LLM semantic review (OpenRouter panel), V4
   oracle-differential testing (upper bound).
4. A silent-failure characterization: the set of (class, severity) cells that
   materially distort revenue statistics (max RDM > 1%) while evading V1+V2,
   with reproducible artifacts (seeds, versions, Zenodo DOI, GitHub).

## 3. Failure taxonomy

| ID | Class | Mechanism | Primary statistic hit | Expected direction |
|----|-------|-----------|----------------------|--------------------|
| F01 | HS leading-zero loss | hs6 cast to int | chapter shares | reallocation |
| F02 | Unit-quantity mismatch | kg vs g on subset | UV screen rate | screen inflation |
| F03 | Stale-FX conversion | prior-month rate | total duty | small bias |
| F04 | CIF/FOB conflation | wrong valuation base | total duty | revenue down |
| F05 | Tariff-vintage misjoin | wrong schedule year | chapter duty | reallocation |
| F06 | Outcome leakage | post-clearance outcome into flag | flag precision | optimistic |
| F07 | Duplicate amendments | originals + amended rows | total duty | revenue up |
| F08 | Null zero-fill | missing value imputed 0 | total duty | revenue down |
| F09 | Partner swap | origin column permuted | origin shares | reallocation |
| F10 | Schema-drift fallback | rename, silent FOB fallback | total duty | revenue down |
| F11 | Dedup overreach | split shipments dropped | total duty | revenue down |
| F12 | Country-code drift | ISO3/numeric mixing | origin shares | fragmentation |

## 4. Substrates

S-A synthetic customs declarations (seeded generator, DATE-like schema; in
repo, fully open). S-B DATE public synthetic customs dataset (local file,
loader provided). S-C CTGAN-generated declarations from the author's existing
privacy-preserving substrate line (local file). S-D (journal extension) UN
Comtrade mirror-statistics extract reusing the PONE triadic-screening ETL.
Nothing confidential; no live NBR data.

## 5. Detection matrix

| Tier | Family | Implementation | Status |
|------|--------|----------------|--------|
| V1 | Rule suite | rules.py (9 rules, baselines learned on clean reference) | implemented, smoke-tested |
| V1b | Tool-native rules | Great Expectations adapter | scaffold, run locally |
| V2 | Drift monitor | Evidently 0.7 DataDriftPreset adapter | implemented, smoke-tested |
| V3 | LLM semantic review | OpenRouter panel (5 models, temp 0, JSON verdicts) | scaffold, needs key |
| V4 | Oracle differential | stats diff vs tasks.py oracles | implemented (defines RDM) |

## 6. Metrics

Detection: per (tier, class, severity): fired rate over seeds; per-tier false
positive rate on clean controls. Severity: RDM per statistic; max-RDM per
cell. Headline: Silent-Failure Rate (SFR) = share of grid cells with
max RDM > 1% and no V1/V2 firing; reported overall, per class, per severity,
and with V3 added. Cost: validator runtime; V3 token cost.

## 7. Experiments

- E1 Pipeline generation: 5-model OpenRouter panel x 5 tasks x k=3 samples,
  frozen prompt (prompts/pipeline_gen_prompt.md); execute generated pipelines
  on clean substrates; measure intrinsic defect rate vs oracle (which taxonomy
  classes LLMs introduce unprompted).
- E2 Injection grid: substrates x 12 classes x severities {0.01, 0.05, 0.20}
  x 5 seeds; RDM profiles. Synthetic-substrate grid (180 cells) already run;
  see docs/PRELIM_GRID_SUMMARY.md.
- E3 Detection matrix: V1, V1b, V2, V3 over the E2 grid; SFR with and without
  the LLM tier; per-class detection curves vs severity.
- E4 Case anatomy: two deep dives (F06 leakage, F09 partner swap) showing how
  a materially wrong national revenue statistic passes a green validation run.

## 8. Preliminary real results (synthetic substrate, this repo, 2 Jul 2026)

180-cell grid (12 x 3 x 5): V1+V2 detect 10 of 12 classes at p >= 0.05 with
zero false positives on clean controls; F06 and F09 are never detected and are
silent in 67% and 60% of their cells respectively; F03 is undetected but
immaterial (max RDM 0.03% at monthly FX drift); F04 escapes at p = 0.01.
Worst single distortion: F01 chapter-share RDM 53.9%. These are scaffold-run
numbers on S-A only; paper results require the full substrate set and E1/E3.

## 9. Venue plan

Conference: ICCIT 2026 (IEEE Bangladesh Section, Cox's Bazar; submission
deadline 31 July 2026), 6-page version covering taxonomy + E2 + V1/V2 + SFR on
two substrates. Journal extension after ICCIT notification (15 Oct 2026):
full matrix incl. V3 panel, Comtrade substrate, E1 intrinsic-defect study.
Ladder: GIQ -> DSS -> IP&M -> ESWA. Research4Life Group A APC waivers apply at
Elsevier venues through Nov 2026.

## 10. US policy anchors

NIST AI Risk Management Framework 1.0 (measurement and management of AI system
risks in deployment); GAO-21-519SP AI Accountability Framework (monitoring and
data-quality dimensions of federal AI oversight); OMB M-24-10 (minimum
practices for safety-impacting and rights-impacting AI in federal agencies,
incl. ongoing monitoring); Federal Data Strategy / Evidence Act (reliability
of statistics used for decisions). Framing: revenue statistics are
decision-critical government data; silent pipeline failures are an
accountability gap these instruments require agencies to close.

## 11. Timeline to ICCIT (target: submit by 29 July 2026)

- Jul 2--6: freeze taxonomy/spec (done); wire DATE + CTGAN loaders; rerun E2
  on S-B/S-C.
- Jul 7--13: E1 generation runs (OpenRouter key on SP's machine); executor
  harness; intrinsic-defect coding.
- Jul 14--19: E3 full matrix incl. V3; SFR tables; detection-vs-severity
  curves.
- Jul 20--25: 6-page IEEE LaTeX draft; figures; internal red-team pass
  (E1--E6-style blocker audit).
- Jul 26--29: polish, reproducibility package, Zenodo deposit (SP releases),
  CMT submission (SP submits).

## 12. Reproducibility and ethics

Fixed seeds; model names/versions/dates logged to manifests; no API keys in
repo (env vars only); public or synthetic data only; AI-generated pipeline
code clearly segregated from human-written code; Zenodo DOI + GitHub
(sushantaresearch) at submission. All references verified before the draft
cites them; the one post-cutoff citation reused from the source notes
(arXiv:2604.09163, Rehberger et al.) was verified live on 2 Jul 2026.

## 13. Related-work spine (verified anchors; full pass during drafting)

Schelter et al., Deequ, VLDB 2018 (automated data-quality verification);
Breck et al., Data Validation for ML, MLSys 2019 (TFX schema/skew validation);
Rehberger et al., arXiv:2604.09163, 2026 (DQ tools measurement + LLM
integration gap); Kim et al., DATE, KDD 2020 (customs fraud substrate);
Xu et al., CTGAN, NeurIPS 2019 (tabular synthesis); Evidently and Great
Expectations documentation for tool versions used.
