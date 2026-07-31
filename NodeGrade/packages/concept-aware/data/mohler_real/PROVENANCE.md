# Real Mohler et al. (2011) dataset — provenance

Downloaded 2026-07-27 from the Hugging Face dataset `nkazi/MohlerASAG`
(https://huggingface.co/datasets/nkazi/MohlerASAG), license CC-BY-4.0.
That repository packages the original Mohler & Mihalcea (2011) "Texas
Extended" ACL-HLT dataset (introductory Data Structures course,
University of North Texas) in parquet form, with a documented extraction
path back to the original 2009/2011 releases.

Files:
- `mohler_open_ended_raw.parquet` — 2,273 open-ended records, columns
  `[id, question, instructor_answer, student_answer, score_grader_1,
  score_grader_2, score_avg]`. This is the full "cleaned/open_ended" split.
- `mohler_annotations_raw.parquet` — annotation metadata (not currently used).

## Why this replaces the previous "Mohler" data

`datasets/mohler_loader.py` previously returned a **hand-authored, fully
synthetic** 120-sample fixture (`MOHLER_SAMPLE_DATA`), not real Mohler
data — its own docstring said the module provides "a sample subset for
testing (embedded)" and "synthetic generation for evaluation pipeline
testing." Every prior evaluation in this project (Paper 1's headline
Table 1, and Experiments #1/#2 run 2026-07-27) was computed against this
fabricated data. See REPRODUCIBILITY.md for the full incident writeup.

## Selection of the KG-aligned subset

The frozen v1.0-expert KG (`data/ds_knowledge_graph.json`) covers Data
Structures topics in depth (linked lists, stacks, queues, arrays, trees/
BSTs, sorting algorithms, recursion). Filtering the real 2,273-record
open-ended set to questions matching these topics (case-insensitive
substring match on question text) yields **45 unique questions, 1,262
total graded responses** (avg 28/question) — see
`mohler_real_kg_aligned.json` for the frozen selection. This is a much
larger and more representative sample than the previous fabricated
120-sample set, and unlike it, is fully traceable to a real, citable,
CC-BY-4.0 public benchmark.

No hash-table or BFS/DFS/graph-traversal questions exist in the real
dataset (unlike the fabricated set's Q5/Q6), so those topics are absent
from the real KG-aligned subset; this is a real property of the dataset,
not a selection choice.
