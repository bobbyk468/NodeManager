"""
Generate FIXED concepts_only ablation prompt.

Bug fixed: original prompt caused Gemini to score 0.0 when matched=none,
ignoring the student answer text entirely.

Fix: student answer vs reference is the PRIMARY evidence;
     matched concept list is SUPPLEMENTARY confirmation only.

Output: /tmp/ablation_concepts_v2.txt
"""

import json, os

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
INTERMEDIATES = os.path.join(BASE_DIR, "data", "ablation_intermediates_gemini_flash_latest.json")

SYSTEM = """You are an expert Computer Science educator grading short-answer exam responses.

TASK: Grade each student answer from 0.0 to 5.0 using 0.25 increments.

GRADING SCALE:
  5.0: Student covers ≥90% of the reference answer content correctly
  4.5: ≥80%, only minor omissions
  4.0: ≥70%, one clear gap
  3.5: ≥60% with reasonable depth
  3.0: ~50%
  2.5: 30-50%, substantial content missing
  2.0: 1-2 key ideas correct, most missing
  1.5: partial understanding of 1 concept, no mechanism
  1.0: aware of topic but no accurate explanations
  0.5: single marginally relevant statement
  0.0: no relevant content

HOW TO GRADE:
  PRIMARY evidence: carefully compare the student's answer against the reference answer.
    Ask: What key concepts from the reference did the student cover? What is missing?
  SUPPLEMENTARY evidence: KG matched concepts and chain coverage percentage.
    These confirm which knowledge-graph concepts were detected in the answer.
    IMPORTANT: If matched concepts = "none" or chain coverage = 0%, do NOT
    automatically give 0. The student may still have relevant content—read
    the answer and score based on what you see.

Return ONLY valid JSON (no markdown, no explanation):
{
  "scores": {
    "<id>": <score>,
    ...
  }
}"""


def build_sample(idx, entry):
    comp     = entry.get("comparison", {})
    analysis = comp.get("analysis", {})
    scores   = comp.get("scores", {})

    matched  = analysis.get("matched_concepts", [])
    chain    = scores.get("chain_coverage", 0.0)

    covered  = ", ".join(matched[:12]) if matched else "none detected"
    chain_s  = f"{chain:.0%}" if chain else "0%"

    return (
        f"--- SAMPLE {idx} ---\n"
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE ANSWER: {entry['reference_answer']}\n\n"
        f"STUDENT ANSWER: {entry['student_answer']}\n\n"
        f"[Supplementary KG evidence]\n"
        f"  Matched concepts: {covered}\n"
        f"  Chain coverage: {chain_s}\n"
        f"  (Note: empty matches do not mean 0 score — read the answer above)"
    )


def main():
    with open(INTERMEDIATES) as f:
        ints = json.load(f)

    n = 120
    entries = [(i, ints[str(i)]) for i in range(n)]

    header = (
        f"{SYSTEM}\n\n"
        f"Grade the following {n} student answers (IDs 0–{n-1}).\n"
        f"Base your score on how well each student answer covers the reference content.\n"
        f"The KG evidence is supplementary — use it to confirm, not to override.\n\n"
        f"{'='*70}\n\n"
    )
    body = "\n\n".join(build_sample(idx, entry) for idx, entry in entries)
    footer = (
        f"\n\n{'='*70}\n"
        f"Return ONLY the JSON with one score per sample ID (0 to {n-1}).\n"
        f"Example: {{\"scores\": {{\"0\": 1.5, \"1\": 3.0, ...}}}}"
    )

    content = header + body + footer
    out_path = "/tmp/ablation_concepts_v2.txt"
    with open(out_path, "w") as f:
        f.write(content)

    print(f"Concepts-only (v2) prompt: {out_path}  ({len(content):,} chars)")
    print(f"\nAfter Gemini responds, save response as:")
    print(f"  /tmp/ablation_concepts_v2_response.json")
    print(f"\nFormat expected: {{\"scores\": {{\"0\": X.X, \"1\": X.X, ...}}}}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, BASE_DIR)
    main()
