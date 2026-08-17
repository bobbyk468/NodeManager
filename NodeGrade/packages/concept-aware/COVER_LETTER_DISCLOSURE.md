# Disclosure Paragraph for Cover Letter

*For inclusion in the cover letter submitted to the editor alongside the
manuscript. Factual statement only; no editorializing beyond what is stated
below.*

---

During internal review, on 2026-07-28, the authors discovered that the
dataset used to compute the headline results in an earlier draft of this
manuscript was not the real Mohler et al. (2011) benchmark it was
represented as, but a hand-authored, fully synthetic 120-sample fixture
generated during early pipeline development and never replaced with real
data before evaluation. This was found by the authors during their own
internal verification process, prior to any submission or external review.
Upon discovery, the authors obtained the real Mohler et al. (2011) dataset
(via the `nkazi/MohlerASAG` release on HuggingFace, CC-BY-4.0) and re-ran
the full evaluation against it: 1,262 responses across 46 questions aligned
with the manuscript's expert knowledge graph. Every quantitative result in
this submission reflects that real-data re-evaluation; none of the
fabricated-data numbers are reported as findings anywhere in this
manuscript. The real-data effect size is smaller than the fabricated-data
result had indicated (an 8.2% MAE reduction versus the fabricated 32.4%),
and the manuscript's discussion and limitations sections report this
directly. A complete, timestamped record of the discovery, verification,
and correction process is maintained in the submission's supplementary
materials (`REPRODUCIBILITY.md`) and is available to the editor and
reviewers in full.

---

**Word count:** 199 words (body paragraph only, excluding this note) — within the 150–250 word target.
