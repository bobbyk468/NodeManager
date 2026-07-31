#!/usr/bin/env python3
"""
build_mohler_real_subset.py — freeze the real, KG-aligned Mohler subset.

Filters the real nkazi/MohlerASAG open-ended records
(data/mohler_real/mohler_open_ended_raw.parquet) to the Data Structures
topics the frozen v1.0-expert KG covers, and writes the frozen selection
to data/mohler_real/mohler_real_kg_aligned.json. See
data/mohler_real/PROVENANCE.md for why this replaces the previous
fabricated 120-sample dataset in datasets/mohler_loader.py.

Run:
    python3 build_mohler_real_subset.py
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data" / "mohler_real"

# Case-insensitive substring keywords matching the frozen KG's DS-topic
# coverage (linked lists, stacks, queues, arrays, trees/BSTs, sorting,
# recursion). Regex, applied to each unique question text.
DS_TOPIC_KEYWORDS = [
    "linked list", "stack", "queue", "binary search tree", "binary tree",
    r"\btree\b", "array", "insertion sort", "selection sort", r"\bsort",
    "recursi",
]


def main() -> int:
    import pandas as pd
    import re

    df = pd.read_parquet(DATA / "mohler_open_ended_raw.parquet")
    unique_questions = df[["id", "question"]].drop_duplicates(subset="question")

    matched_questions: set[str] = set()
    for kw in DS_TOPIC_KEYWORDS:
        hits = unique_questions[unique_questions["question"].str.contains(
            kw, case=False, na=False, regex=True)]
        matched_questions.update(hits["question"])

    subset = df[df["question"].isin(matched_questions)].copy()
    # Stable per-question id: E03.Q06 etc. (strip the .A## response suffix)
    subset["qid"] = subset["id"].str.replace(r"\.A\d+$", "", regex=True)

    rows = []
    for _, r in subset.iterrows():
        rows.append({
            "id": r["id"],
            "qid": r["qid"],
            "question": r["question"].replace(" <STOP>", "").strip(),
            "reference_answer": r["instructor_answer"].replace(" <STOP>", "").strip(),
            "student_answer": r["student_answer"].replace(" <STOP>", "").strip(),
            "score_grader_1": float(r["score_grader_1"]),
            "score_grader_2": float(r["score_grader_2"]),
            "score_avg": float(r["score_avg"]),
        })

    qids = sorted(set(r["qid"] for r in rows))
    out = {
        "source": "nkazi/MohlerASAG (HuggingFace, CC-BY-4.0), derived from "
                   "Mohler & Mihalcea (2011) ACL-HLT Texas Extended dataset",
        "selection": "DS-topic keyword match against frozen v1.0-expert KG coverage",
        "n_questions": len(qids),
        "n_responses": len(rows),
        "question_ids": qids,
        "samples": rows,
    }
    out_path = DATA / "mohler_real_kg_aligned.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Questions: {len(qids)}  Responses: {len(rows)}")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
