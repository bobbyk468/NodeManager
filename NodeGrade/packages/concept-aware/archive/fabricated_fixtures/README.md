# Fabricated Fixtures (Quarantined)

This directory holds data files that were computed against, or represent,
the fabricated 120-sample Mohler fixture discovered and retracted during
internal review on 2026-07-28. See
[../../REPRODUCIBILITY.md](../../REPRODUCIBILITY.md) for the full incident
record.

## `mohler_eval_results.json`

The fabricated, hand-authored 120-sample fixture that an earlier draft of
Paper 1 mistook for the real Mohler et al. (2011) benchmark. It is kept
here, unmodified, because several scripts intentionally still read it to
reproduce the retracted historical result for the supplementary record
(e.g. `compute_clustered_significance.py`'s default `--eval` path,
`compute_human_irr_and_per_question.py`). **Its numbers (n=120, 32.4% MAE
reduction, etc.) are retracted and must never be cited as a current claim
in either paper** — the real, current result is n=1,262, 8.2% MAE
reduction, reproducible via `verify_all_paper_claims.py` and the scripts
listed in REPRODUCIBILITY.md's master verification command.

Moved here from `data/mohler_eval_results.json` on 2026-08-17 as part of
the publication-readiness pass (Task: quarantine fabricated-fixture
code/data), so it is no longer sitting next to the real, current data
files in `data/` where it could be mistaken for one.
