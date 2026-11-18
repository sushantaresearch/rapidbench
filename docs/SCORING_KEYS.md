# E1 scoring note: dict-key canonicalization (v0.4)

Trial run (k=1, 2 Jul 2026) showed 4/5 models verdicted
defective:s2_chapter_duty_share. Reproduction of one generated pipeline in
the sandbox executor showed s2 RDM 0.5394 with every other statistic at
exactly 0: the model used the CSV's `chapter` column, pandas inferred it as
integer, and JSON emitted keys '1','2','3','8' where the oracle holds
'01','02','03','08'. Values identical; keys de-padded. That is a formatting
difference introduced by CSV round-tripping, not an analytical defect.

Fix: `executor._canon` zero-pads pure-digit dict keys of length <= 2 on both
sides before RDM. Regression pair enforced in tests/test_panel_mock.py:

- mock/chapter-col-correct (uses `chapter` column, no dtype): was
  defective:s2 at 0.5394, now correct at s2 RDM 0.0.
- mock/bug-hs-dtype (derives chapter from hs6 read as int, the genuine
  leading-zero trap): stays defective:s2 at 0.539, because a chapter like
  '38' derived from '038475' is two digits already and remains wrong.

The canonicalization therefore removes only format-level false defects and
cannot mask genuine duty misattribution. Documented for the paper's
methods section; the k=1 trial predates this fix and is not reported.

Also in v0.4: OpenRouter max_tokens raised 2000 -> 8000. Reasoning models
spend thinking tokens from the same completion budget; 2000 risks
truncated code (suspected cause of the gemini-2.5-pro trial crash,
pending confirmation from the trial error log).
