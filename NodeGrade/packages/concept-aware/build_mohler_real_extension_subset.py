#!/usr/bin/env python3
"""
build_mohler_real_extension_subset.py — freeze a small EXTENSION to the
real, KG-aligned Mohler subset (2026-07-28).

The original build_mohler_real_subset.py used substring keyword matching
against the question text (DS_TOPIC_KEYWORDS) and missed 4 genuinely
in-KG-domain questions because their question text doesn't literally
contain a keyword (e.g. "What is a leaf?" doesn't contain "tree"; "How
are infix expressions evaluated by computers?" doesn't contain "stack").
Manually identified by inspecting all 35 unused real questions in
data/mohler_real/mohler_open_ended_raw.parquet.

This does NOT modify or regenerate data/mohler_real/mohler_real_kg_aligned.json
(the frozen 46-question/1,262-response reproducibility anchor for every
number in the paper so far -- see REPRODUCIBILITY.md, "Do not regenerate
this file"). It writes a separate extension file with the same schema;
downstream Phase A/B scripts and the final merge are separate steps.

Run:
    python3 build_mohler_real_extension_subset.py
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data" / "mohler_real"

# Manually identified, genuinely in-KG-domain questions missed by the
# original keyword matcher's literal substring matching.
EXTENSION_QIDS = {
    "E08.Q06": "infix/postfix expression evaluation -- stack-based (Data Structures: stacks)",
    "E10.Q03": "'what is a leaf' -- tree terminology (Data Structures: trees/BSTs)",
    "E11.Q09": "divide-and-conquer paradigm -- recursion/sorting-adjacent (Data Structures: recursion, sorting)",
    "E12.Q02": "experimental algorithm-timing methodology -- borderline; the pipeline's own "
               "out-of-KG-domain detector will determine assessability, not this script",
}


def main() -> int:
    import pandas as pd

    df = pd.read_parquet(DATA / "mohler_open_ended_raw.parquet")
    df["qid"] = df["id"].str.replace(r"\.A\d+$", "", regex=True)

    with (DATA / "mohler_real_kg_aligned.json").open() as f:
        existing = json.load(f)
    existing_qids = set(existing["question_ids"])
    overlap = existing_qids & set(EXTENSION_QIDS)
    assert not overlap, f"Extension qids overlap the frozen 46-question set: {overlap}"

    subset = df[df["qid"].isin(EXTENSION_QIDS)].copy()

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
        "selection": "Manually identified DS-topic questions missed by the original "
                     "keyword-matcher's literal substring matching; extension to "
                     "mohler_real_kg_aligned.json, frozen 2026-07-28",
        "extension_rationale": EXTENSION_QIDS,
        "n_questions": len(qids),
        "n_responses": len(rows),
        "question_ids": qids,
        "samples": rows,
    }
    out_path = DATA / "mohler_real_kg_extension.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Extension questions: {len(qids)}  Responses: {len(rows)}")
    for q in qids:
        n = sum(1 for r in rows if r["qid"] == q)
        print(f"  {q}: n={n}")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
