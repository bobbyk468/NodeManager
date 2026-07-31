"""
Mohler Dataset Loader.

Loads the REAL Mohler et al. (2011) CS Short Answer Grading dataset,
filtered to the Data Structures-topic KG-aligned subset frozen in
data/mohler_real/mohler_real_kg_aligned.json (46 questions, 1,262
responses; see data/mohler_real/PROVENANCE.md).

2026-07-27 correction: this module previously returned a hand-authored,
fully SYNTHETIC 120-sample fixture (`MOHLER_SAMPLE_DATA`) instead of real
data -- every evaluation in this project (Paper 1's Table 1, and
Experiments #1/#2) was computed against fabricated student answers and
scores. That fixture has been removed. See REPRODUCIBILITY.md for the
full incident writeup and data/mohler_real/PROVENANCE.md for how the
real replacement dataset was sourced and verified.

Reference:
  Mohler, M., Bunescu, R., & Mihalcea, R. (2011).
  "Learning to Grade Short Answer Questions using Semantic Similarity
  Measures and Dependency Graph Alignments"
  ACL-HLT 2011.
  Real data via nkazi/MohlerASAG (HuggingFace, CC-BY-4.0).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data" / "mohler_real"
_FROZEN_PATH = _DATA_DIR / "mohler_real_kg_aligned.json"


@dataclass
class MohlerSample:
    """A single sample from the Mohler dataset."""
    question_id: str
    question: str
    reference_answer: str
    student_answer: str
    score_me: float  # Score from annotator 1
    score_other: float  # Score from annotator 2
    score_avg: float  # Average of both annotators
    sample_id: str = ""  # Original record id (e.g. "E07.Q01.A03"), unique per response

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "reference_answer": self.reference_answer,
            "student_answer": self.student_answer,
            "score_me": self.score_me,
            "score_other": self.score_other,
            "score_avg": self.score_avg,
            "sample_id": self.sample_id,
        }


@dataclass
class MohlerDataset:
    """Container for the Mohler dataset."""
    samples: list[MohlerSample] = field(default_factory=list)
    questions: dict = field(default_factory=dict)  # qid → question text

    @property
    def num_samples(self) -> int:
        return len(self.samples)

    @property
    def num_questions(self) -> int:
        return len(self.questions)

    def get_by_question(self, qid: str) -> list[MohlerSample]:
        return [s for s in self.samples if s.question_id == qid]

    def score_distribution(self) -> dict:
        dist = {}
        for s in self.samples:
            rounded = round(s.score_avg)
            dist[rounded] = dist.get(rounded, 0) + 1
        return dict(sorted(dist.items()))


def load_mohler_sample(n_per_question: int = 0) -> MohlerDataset:
    """
    Load the real, KG-aligned Mohler subset (46 questions, 1,262 responses
    by default) from the frozen data/mohler_real/mohler_real_kg_aligned.json.

    Parameters
    ----------
    n_per_question : If > 0, cap each question to its first this-many
                     responses (in frozen-file order). Default 0 = load all.
    """
    with _FROZEN_PATH.open() as f:
        frozen = json.load(f)

    dataset = MohlerDataset()
    per_q_count: dict[str, int] = {}

    for row in frozen["samples"]:
        qid = row["qid"]
        if n_per_question > 0:
            per_q_count[qid] = per_q_count.get(qid, 0)
            if per_q_count[qid] >= n_per_question:
                continue
            per_q_count[qid] += 1

        dataset.questions[qid] = row["question"]
        dataset.samples.append(MohlerSample(
            question_id=qid,
            question=row["question"],
            reference_answer=row["reference_answer"],
            student_answer=row["student_answer"],
            score_me=row["score_grader_1"],
            score_other=row["score_grader_2"],
            score_avg=row["score_avg"],
            sample_id=row["id"],
        ))

    return dataset


def dev_test_split(dataset: MohlerDataset, dev_fraction: float = 0.25) -> tuple[list[int], list[int]]:
    """
    Canonical, deterministic dev/test split, question-stratified, replacing
    the old dataset's fixed "12 responses/question, indices 0-2 = dev"
    convention (which assumed every question had exactly 12 responses --
    false for the real dataset, where counts range 24-31).

    Per question: sort responses by (score_avg, sample_id) for a stable
    order, then assign every 4th response (index 0, 4, 8, ...) to dev and
    the rest to test. This is SYSTEMATIC sampling across the sorted score
    range -- chosen instead of "lowest 25% of scores" or "first 25% by
    dataset order" specifically so dev and test have similar score
    distributions (matching the paper's documented intent: "stratified by
    question to preserve score distribution"), rather than dev
    over-representing one end of the score range.

    Returns (dev_indices, test_indices), each a list of positions into
    dataset.samples (NOT sample ids), so callers can build numpy arrays
    directly via dataset.samples[i].

    This function is the SINGLE SOURCE OF TRUTH for the dev/test partition
    -- every script that previously computed `test_mask = (i % 12) >= 3`
    should call this instead.
    """
    step = max(1, round(1.0 / dev_fraction))  # dev_fraction=0.25 -> step=4

    by_qid: dict[str, list[int]] = {}
    for i, s in enumerate(dataset.samples):
        by_qid.setdefault(s.question_id, []).append(i)

    dev_indices: list[int] = []
    test_indices: list[int] = []
    for qid, idxs in by_qid.items():
        ordered = sorted(idxs, key=lambda i: (dataset.samples[i].score_avg, dataset.samples[i].sample_id))
        for pos, i in enumerate(ordered):
            if pos % step == 0:
                dev_indices.append(i)
            else:
                test_indices.append(i)

    return dev_indices, test_indices
