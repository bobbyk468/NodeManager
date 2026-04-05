"""
Merge the two Kaggle ASAG KG response files into one complete KG file.

Reads:
  /tmp/auto_kg_response_kaggle_asag.json       (questions 0-52)
  /tmp/auto_kg_response_kaggle_asag_part2.json (questions 53-149)

Writes:
  /tmp/auto_kg_response_kaggle_asag.json       (merged, all 150 questions)

Then regenerates batch scoring prompts for the full dataset.
"""

from __future__ import annotations
import json
import os
import subprocess

def main():
    p1 = "/tmp/auto_kg_response_kaggle_asag.json"
    p2 = "/tmp/auto_kg_response_kaggle_asag_part2.json"

    if not os.path.exists(p2):
        print(f"ERROR: {p2} not found.")
        print("Send /tmp/auto_kg_prompt_kaggle_asag_part2.txt to Gemini first.")
        return

    with open(p1) as f: part1 = json.load(f)
    with open(p2) as f: part2 = json.load(f)

    kgs1 = part1.get("question_kgs", {})
    kgs2 = part2.get("question_kgs", {})

    merged = {"question_kgs": {**kgs1, **kgs2}}
    n = len(merged["question_kgs"])
    print(f"Merged: {len(kgs1)} + {len(kgs2)} = {n} question KGs")

    with open(p1, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"Saved merged KG → {p1}")

    # Regenerate batch prompts with full KG coverage
    print("\nRegenerating batch scoring prompts with full KG coverage...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        ["python3", "generate_batch_scoring_prompts.py", "--dataset", "kaggle_asag"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("ERROR:", result.stderr)


if __name__ == "__main__":
    main()
