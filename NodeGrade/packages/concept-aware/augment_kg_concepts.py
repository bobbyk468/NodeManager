"""
Post-hoc Concept Augmentation Script.

Scans student answers for Q3 (IDs 36-47) and Q9 (IDs 108-119) to detect
complexity class mentions and other concepts that the standard extractor misses.
Saves augmented intermediates to data/ablation_intermediates_augmented.json.

Usage:
    python3 augment_kg_concepts.py
"""

from __future__ import annotations

import copy
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

INPUT_FILE = os.path.join(DATA_DIR, "ablation_intermediates_gemini_flash_latest.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "ablation_intermediates_augmented.json")

SEP = "─" * 72


# ─────────────────────────────────────────────────────────────────────────────
# Q9 detection patterns — order matters (more specific first)
# ─────────────────────────────────────────────────────────────────────────────

def detect_q9_concepts(text: str) -> set[str]:
    """Return set of concept IDs detected in the student answer text (Q9)."""
    found: set[str] = set()
    t = text.lower()

    # O(n log n) — must check before O(n) to avoid false split
    if re.search(r"o\s*\(\s*n\s+log\s*n\s*\)", t) or re.search(r"n\s*log\s*n", t):
        found.add("o_n_log_n")

    # O(n²) / O(n^2) / O(n2) / "quadratic"
    if (re.search(r"o\s*\(\s*n\s*[²2\^]\s*2?\s*\)", t) or
            re.search(r"o\s*\(\s*n\^2\s*\)", t) or
            "quadratic" in t):
        found.add("o_n2")

    # O(log n) / "logarithmic"
    if re.search(r"o\s*\(\s*log\s*n\s*\)", t) or "logarithmic" in t:
        found.add("o_log_n")

    # O(1) / "constant time"
    if re.search(r"o\s*\(\s*1\s*\)", t) or "constant time" in t:
        found.add("o_1")

    # O(n) — only if NOT part of O(n log n) or O(n²)
    # Use word-boundary to avoid matching "O(n log n)" again
    if re.search(r"o\s*\(\s*n\s*\)(?!\s*log)", t):
        found.add("o_n")

    # "linear" in complexity context — not the word "linearithmic" alone
    if re.search(r"\blinear\b", t) and "linearithmic" not in t:
        found.add("o_n")

    # Specific sorting algorithms (also adds algorithm complexity implicitly)
    if re.search(r"merge\s*sort|mergesort", t):
        found.add("merge_sort")
    if re.search(r"bubble\s*sort|bubblesort", t):
        found.add("bubble_sort")
    if re.search(r"heap\s*sort|heapsort", t):
        found.add("heap_sort")

    # Efficiency / performance language → time_complexity chain
    # "efficient", "efficiency", "fast", "slow", "speed", "performance", "run time"
    if re.search(r"\beffici(ent|ency)\b|\bspeed\b|\bhow fast\b|\brun.?time\b|\bperformance\b", t):
        found.add("time_complexity")

    # "algorithm" mentioned explicitly (many Big-O answers reference it)
    if re.search(r"\balgorithm\b", t):
        found.add("algorithm")

    return found


# ─────────────────────────────────────────────────────────────────────────────
# Q3 detection patterns
# ─────────────────────────────────────────────────────────────────────────────

def detect_q3_concepts(text: str) -> set[str]:
    """Return set of concept IDs detected in the student answer text (Q3)."""
    found: set[str] = set()
    t = text.lower()

    if "balanced" in t:
        found.add("balanced_tree")

    if re.search(r"subtree|sub-tree|left\s+subtree|right\s+subtree", t):
        found.add("subtree")

    # BST worst case is O(n) — unbalanced chain
    if re.search(r"worst\s*case", t):
        found.add("o_n")

    return found


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("Post-hoc Concept Augmentation")
    print(SEP)

    with open(INPUT_FILE) as f:
        data = json.load(f)

    augmented = copy.deepcopy(data)

    total_additions = 0
    report_rows = []

    for sid_str, sample in data.items():
        sid = int(sid_str)
        answer = sample.get("student_answer", "")
        existing = set(
            augmented[sid_str]["comparison"]["analysis"].get("matched_concepts", [])
        )

        additions: set[str] = set()

        # Q9: IDs 108-119
        if 108 <= sid <= 119:
            new_concepts = detect_q9_concepts(answer)
            additions = new_concepts - existing

        # Q3: IDs 36-47
        elif 36 <= sid <= 47:
            new_concepts = detect_q3_concepts(answer)
            additions = new_concepts - existing

        if additions:
            updated = sorted(existing | additions)
            augmented[sid_str]["comparison"]["analysis"]["matched_concepts"] = updated
            total_additions += len(additions)
            report_rows.append((sid, sorted(additions), sorted(existing), sorted(updated)))

    # Report
    if report_rows:
        print(f"\n{'ID':>4}  {'Added':30}  {'Before → After count'}")
        print("─" * 72)
        for sid, added, before, after in report_rows:
            q = "Q9" if 108 <= sid <= 119 else "Q3"
            print(f"{sid:>4} [{q}]  +{added!s:40}  {len(before)} → {len(after)}")
    else:
        print("No augmentations detected.")

    print(SEP)
    print(f"Total concept additions across all samples: {total_additions}")
    print(f"Samples modified: {len(report_rows)}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(augmented, f, indent=2)
    print(f"\nSaved augmented intermediates → {OUTPUT_FILE}")
    print(SEP)


if __name__ == "__main__":
    main()
