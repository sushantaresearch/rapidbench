# E1 failure mechanisms (panel of 2 Jul 2026, v0.4 harness)

Panel: 5 models x k=3, temperature 0.2, prompt sha256/16 `7a5e9d107eecb4ea`,
synthetic clean substrate n=20000 seed 42. Verdicts: 12 correct, 2 defective,
1 crash. Source files under `results/e1_pipelines/`. Unique code count:
14 of 15 (Claude Sonnet 4.5 emitted byte-identical code in samples 1 and 2,
sha `f3056cb9c574`).

## Defect: unit-convention violation (Llama 3.3 70B, samples 0 and 1)

Shas `357f96ab94cf` and `0809ae6a7622` - two independent generations, same
defect. Both compute every statistic correctly, then multiply exactly the
two scalar share statistics by 100:

    return (uv_below_half_median.sum() / len(df)) * 100   # s4
    return (top_origin_duty / total_duty) * 100           # s5

RDM = |100x - x| / x = 99.0 on both, machine-exact, while s1/s2/s3 are
RDM 0. The chapter-share dictionary (s2) - the same word "share" in the
spec - is emitted as fractions in the same pipelines. One pipeline, two
conventions. A downstream consumer treating 12.3 as a share is silently
wrong by two orders of magnitude; this is a genuine defect, not a scoring
artifact, and canonicalization does not (and should not) forgive it.

## Crash: truncated completion (Gemini 2.5 Pro, sample 2)

Sha `541b439651f4`, runtime 74s (vs 56s and 45s for its two correct
siblings). The saved file begins with a live ```` ```python ```` fence and
ends mid-dict-comprehension - the completion was cut off before the closing
fence. The extractor's complete-fenced-block regex therefore found no block
and fell back to the raw reply, so the opening fence became line 1 of the
executed file (`SyntaxError` at line 1). Two harness changes follow:

1. `extract_code` now strips dangling fence lines on fallback
   (regression: `mock/truncated-fence` -> still `crash`, saved file
   contains no fence). The verdict is unchanged either way - the code is
   unterminated - but the executed artifact no longer contains transport
   syntax.
2. The results CSV now records `finish_reason` per sample, so budget
   truncation (`length`) is diagnosable from the CSV without opening
   source files. The 2 Jul panel predates this column; truncation there
   is inferred from the cut-off source, which is directly observable.

## Scoring adjudication (documented in SCORING_KEYS.md)

Dict keys are canonicalized (zero-pad pure-digit keys, len<=2) before RDM:
CSV round-tripping de-pads chapter keys ('03' -> 3), a format-only
difference that pre-fix convicted 4 of 5 substantively correct sample-0
pipelines. Validation on identical code: DeepSeek sha `eda7ab179677`
appears in the pre-fix trial (convicted `defective:s2`, values equal) and
in the k=3 run (verdicted `correct`). The genuine leading-zero trap
(chapter taken from a de-padded hs6 int) remains flagged.
