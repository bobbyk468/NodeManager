"""
Generate FIXED taxonomy_only ablation prompt.

Bug fixed: original prompt displayed "SOLO: Relational (4/5)" which caused
Gemini to treat it as a score proxy → all SOLO=4 answers capped at 3.0.

Fix: display SOLO/Bloom as qualitative descriptors only (no numeric scale).
     Add explicit instruction that these describe HOW the student thinks,
     not WHAT score to assign.

Output: /tmp/ablation_taxonomy_v2.txt
"""

import json, os

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
INTERMEDIATES = os.path.join(BASE_DIR, "data", "ablation_intermediates_gemini_flash_latest.json")

# Qualitative descriptions for SOLO levels — NO numbers shown
SOLO_DESC = {
    1: "no relevant structure (isolated fragments, no coherent answer)",
    2: "single relevant idea addressed, other aspects ignored",
    3: "several relevant ideas listed but not connected or integrated",
    4: "ideas are integrated into a coherent understanding with relationships explained",
    5: "ideas are generalized beyond the question to new contexts or principles",
}

# Qualitative descriptions for Bloom's levels — NO numbers shown
BLOOM_DESC = {
    1: "recall only (defines or restates terms)",
    2: "comprehension (explains in own words)",
    3: "application (applies to examples)",
    4: "analysis (breaks down, compares, contrasts)",
    5: "synthesis/evaluation (critiques, designs, or evaluates)",
    6: "creation (builds or generates new ideas)",
}

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
    Ask: What key content from the reference did the student cover? What is missing?
  CONTEXTUAL clues: SOLO cognitive level and Bloom's cognitive level describe the
    QUALITY OF THINKING shown in the answer — how the student organizes ideas.
    IMPORTANT: These are qualitative descriptors of cognitive style, NOT score proxies.
    A SOLO=Relational student (who connects ideas well) typically earns a HIGH score,
    but the exact score depends on CONTENT COVERAGE — examine what they actually said.
    Do NOT mechanically map SOLO level to a score.

Return ONLY valid JSON (no markdown, no explanation):
{
  "scores": {
    "<id>": <score>,
    ...
  }
}"""


def build_sample(idx, entry):
    blooms = entry.get("blooms") or {}
    solo   = entry.get("solo")   or {}

    sl_lv   = solo.get("level", 1)
    sl_lbl  = solo.get("label", "Prestructural")
    bl_lv   = blooms.get("level", 1)
    bl_lbl  = blooms.get("label", "Remember")

    solo_desc  = SOLO_DESC.get(sl_lv, SOLO_DESC[1])
    bloom_desc = BLOOM_DESC.get(bl_lv, BLOOM_DESC[1])

    return (
        f"--- SAMPLE {idx} ---\n"
        f"QUESTION: {entry['question']}\n\n"
        f"REFERENCE ANSWER: {entry['reference_answer']}\n\n"
        f"STUDENT ANSWER: {entry['student_answer']}\n\n"
        f"[Contextual cognitive clues]\n"
        f"  SOLO level — {sl_lbl}: {solo_desc}\n"
        f"  Bloom's level — {bl_lbl}: {bloom_desc}\n"
        f"  (These describe how the student thinks — score based on content coverage)"
    )


def main():
    with open(INTERMEDIATES) as f:
        ints = json.load(f)

    n = 120
    entries = [(i, ints[str(i)]) for i in range(n)]

    header = (
        f"{SYSTEM}\n\n"
        f"Grade the following {n} student answers (IDs 0–{n-1}).\n"
        f"Base your score on content coverage vs the reference. "
        f"Use the SOLO/Bloom clues as context only.\n\n"
        f"{'='*70}\n\n"
    )
    body = "\n\n".join(build_sample(idx, entry) for idx, entry in entries)
    footer = (
        f"\n\n{'='*70}\n"
        f"Return ONLY the JSON with one score per sample ID (0 to {n-1}).\n"
        f"Example: {{\"scores\": {{\"0\": 1.5, \"1\": 3.0, ...}}}}"
    )

    content = header + body + footer
    out_path = "/tmp/ablation_taxonomy_v2.txt"
    with open(out_path, "w") as f:
        f.write(content)

    print(f"Taxonomy-only (v2) prompt: {out_path}  ({len(content):,} chars)")
    print(f"\nAfter Gemini responds, save response as:")
    print(f"  /tmp/ablation_taxonomy_v2_response.json")
    print(f"\nFormat expected: {{\"scores\": {{\"0\": X.X, \"1\": X.X, ...}}}}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, BASE_DIR)
    main()
