#!/usr/bin/env python3
"""
compute_taxonomy_kappa.py — Machine-IRR proxy for the 16-entry CS Misconception
Taxonomy used in Paper 1, §3.4.

Two independent coding methods are applied to the 120 Mohler KG-aligned answers
(or a sub-sample); we compute Cohen's kappa per taxonomy entry and a
micro-/macro-averaged kappa across the taxonomy.

CODER A (KG-rule): a concept's *id* must overlap with a taxonomy entry's
`concepts` list AND the student must show a low-score (avg < 3.0) — i.e. KG
evidence + outcome trigger. Operationalises "rule + KG" coding.

CODER B (lexical): a taxonomy entry's `common_claim` keywords must appear in
the student's answer via stemmed-bag-of-words overlap above a threshold.
Operationalises "lexical-only" coding (a different evidence channel).

This is a *machine-IRR pilot* — designed to bound expected agreement before a
human second-coder pass. Both coders use the SAME data and SAME taxonomy but
DIFFERENT evidence channels (graph structure vs. text surface), so kappa
reflects construct-validity overlap between the two channels.

Run:
    python compute_taxonomy_kappa.py [--n 30] [--all]

Output (stdout + JSON file):
    - kappa per taxonomy entry (16 entries)
    - micro-averaged kappa (pooled 2x2 table over all entries)
    - macro-averaged kappa (mean of per-entry kappas, ignoring NaN)
    - prevalence + agreement-on-positive for each entry (sanity)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from datasets.mohler_loader import load_mohler_sample, MohlerSample  # noqa: E402
from misconception_detection.detector import CS_MISCONCEPTION_TAXONOMY  # noqa: E402

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "with", "and", "or", "but", "not",
    "by", "as", "at", "from", "this", "that", "these", "those", "it",
    "its", "you", "your", "i", "we", "they", "he", "she", "him", "her",
    "have", "has", "had", "do", "does", "did", "can", "could", "would",
    "should", "may", "might", "will", "shall", "than", "then", "if",
    "so", "into", "out", "up", "down", "over", "under", "also",
}


def tokenise(text: str) -> set[str]:
    toks = re.findall(r"[a-z][a-z0-9_]+", text.lower())
    return {t for t in toks if t not in STOPWORDS and len(t) >= 3}


_PHRASE_STOP = {"a", "an", "the", "is", "are", "of", "to", "for", "in", "on",
                "with", "that", "this", "by", "be", "as", "or", "and"}


def _has_distinctive_phrase(ans_text_lower: str, ans_tokens: set[str], t: dict) -> bool:
    """Framework Fix #4 (2026-05-31): both coders require a distinctive_phrase
    match. Distinctive phrases are short symptomatic strings (e.g. "stack fifo",
    "always o(1)", "encrypt for security") that identify a specific
    misconception rather than just its topic. We match via:

      (a) full literal substring (catches contiguous phrasings like
          "encryption for security"), OR
      (b) all phrase tokens present in the answer in any order
          (catches paraphrases like "stack uses FIFO order" matching
          phrase "stack fifo").

    Stop words are stripped from phrase tokens before set inclusion so
    "stack is fifo" matches phrase "stack fifo".
    """
    phrases = t.get("distinctive_phrases", [])
    if not phrases:
        return False
    for p in phrases:
        p_low = p.lower()
        # (a) full substring
        if p_low in ans_text_lower:
            return True
        # (b) all content tokens present in answer (any order)
        p_tokens = {w for w in re.findall(r"[a-z0-9_]+", p_low)
                    if w not in _PHRASE_STOP and len(w) >= 2}
        # special-case very short tokens like "n" used in "o(n)" — also try matching
        # the bare phrase with parens stripped
        if not p_tokens:
            continue
        if p_tokens.issubset(ans_tokens):
            return True
    return False


def coder_a_kg_rule(sample: MohlerSample, taxonomy: dict) -> set[str]:
    """KG-rule coder: low-score + concept overlap + distinctive_phrase match."""
    # Use score_avg as the outcome trigger
    if sample.score_avg >= 3.0:
        return set()
    ans_tokens = tokenise(sample.student_answer)
    ans_text_lower = sample.student_answer.lower()
    out: set[str] = set()
    for tid, t in taxonomy.items():
        # 1. Concept overlap (any concept word appears in answer tokens)
        tax_concepts = {c.replace("_", " ") for c in t.get("concepts", [])}
        concept_match = False
        for c in tax_concepts:
            words = c.split()
            if any(w in ans_tokens for w in words):
                concept_match = True
                break
        if not concept_match:
            continue
        # 2. NEW: distinctive_phrase must also be present (eliminates false alarms
        #    from topical-but-not-misconception answers)
        if not _has_distinctive_phrase(ans_text_lower, ans_tokens, t):
            continue
        out.add(tid)
    return out


def coder_b_lexical(sample: MohlerSample, taxonomy: dict, k_min: int = 2) -> set[str]:
    """Lexical coder: common_claim keyword overlap above threshold k_min,
    AND distinctive_phrase match (shared with coder A)."""
    ans_tokens = tokenise(sample.student_answer)
    ans_text_lower = sample.student_answer.lower()
    out: set[str] = set()
    for tid, t in taxonomy.items():
        claim_tokens = tokenise(t.get("common_claim", "") + " " + t.get("description", ""))
        overlap = len(ans_tokens & claim_tokens)
        if overlap < k_min:
            continue
        if not _has_distinctive_phrase(ans_text_lower, ans_tokens, t):
            continue
        out.add(tid)
    return out


def cohen_kappa_2x2(a: Sequence[int], b: Sequence[int]) -> tuple[float, dict]:
    """Cohen's kappa for binary labels. Returns (kappa, info)."""
    assert len(a) == len(b)
    n = len(a)
    if n == 0:
        return float("nan"), {"n": 0}
    a11 = sum(1 for x, y in zip(a, b) if x == 1 and y == 1)
    a00 = sum(1 for x, y in zip(a, b) if x == 0 and y == 0)
    a10 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    a01 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    po = (a11 + a00) / n
    p_pos_a = (a11 + a10) / n
    p_pos_b = (a11 + a01) / n
    pe = p_pos_a * p_pos_b + (1 - p_pos_a) * (1 - p_pos_b)
    if pe == 1.0:
        # Both coders unanimous, perfect agreement by chance — kappa undefined
        kappa = float("nan")
    else:
        kappa = (po - pe) / (1 - pe)
    return kappa, {
        "n": n,
        "po": round(po, 4),
        "pe": round(pe, 4),
        "prev_a": round(p_pos_a, 4),
        "prev_b": round(p_pos_b, 4),
        "a11": a11, "a00": a00, "a10": a10, "a01": a01,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=30,
                        help="Sample size for the kappa computation (default 30)")
    parser.add_argument("--all", action="store_true",
                        help="Use all 120 samples (overrides --n)")
    parser.add_argument("--k-min", type=int, default=2,
                        help="Lexical coder overlap threshold (default 2)")
    parser.add_argument("--out", default="data/taxonomy_kappa_results.json",
                        type=Path)
    args = parser.parse_args()

    dataset = load_mohler_sample()
    samples = dataset.samples
    if not args.all:
        # Deterministic stride to span all 10 questions evenly
        stride = max(1, len(samples) // args.n)
        samples = samples[::stride][:args.n]
    print(f"Using n={len(samples)} samples (from {len(dataset.samples)} total).")

    tax = CS_MISCONCEPTION_TAXONOMY
    tax_ids = sorted(tax.keys())

    # Build per-entry binary label vectors for both coders
    labels_a: dict[str, list[int]] = {tid: [] for tid in tax_ids}
    labels_b: dict[str, list[int]] = {tid: [] for tid in tax_ids}

    for s in samples:
        a_set = coder_a_kg_rule(s, tax)
        b_set = coder_b_lexical(s, tax, k_min=args.k_min)
        for tid in tax_ids:
            labels_a[tid].append(1 if tid in a_set else 0)
            labels_b[tid].append(1 if tid in b_set else 0)

    # Per-entry kappa
    per_entry: dict[str, dict] = {}
    kappas_macro: list[float] = []
    pool_a: list[int] = []
    pool_b: list[int] = []
    for tid in tax_ids:
        k, info = cohen_kappa_2x2(labels_a[tid], labels_b[tid])
        per_entry[tid] = {
            "category": tax[tid]["category"],
            "kappa": None if (k != k) else round(k, 4),  # NaN check
            "info": info,
        }
        if k == k:  # not NaN
            kappas_macro.append(k)
        pool_a.extend(labels_a[tid])
        pool_b.extend(labels_b[tid])

    # Macro
    macro = sum(kappas_macro) / len(kappas_macro) if kappas_macro else float("nan")
    # Micro (pooled 2x2)
    micro, micro_info = cohen_kappa_2x2(pool_a, pool_b)

    out = {
        "method": "machine-IRR pilot (Coder A = KG-rule, Coder B = lexical)",
        "n_samples": len(samples),
        "n_taxonomy_entries": len(tax_ids),
        "k_min_lexical": args.k_min,
        "macro_kappa": round(macro, 4) if macro == macro else None,
        "macro_kappa_n_entries": len(kappas_macro),
        "micro_kappa_pooled": round(micro, 4) if micro == micro else None,
        "micro_info": micro_info,
        "per_entry": per_entry,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))

    # Pretty-print summary
    print()
    print(f"Macro-averaged Cohen's kappa  : {out['macro_kappa']} "
          f"({len(kappas_macro)}/{len(tax_ids)} entries had defined kappa)")
    print(f"Micro-averaged Cohen's kappa  : {out['micro_kappa_pooled']} "
          f"(pooled over {micro_info['n']} entry×sample cells)")
    print(f"  positives by Coder A (rule) : {micro_info['a11'] + micro_info['a10']}")
    print(f"  positives by Coder B (lex.) : {micro_info['a11'] + micro_info['a01']}")
    print(f"  unanimous-positive cells    : {micro_info['a11']}")
    print(f"  unanimous-negative cells    : {micro_info['a00']}")
    print()
    print("Per-entry kappa (with prevalence):")
    print(f"  {'ID':<14}  {'Category':<22}  {'kappa':>7}  {'prev_A':>7}  {'prev_B':>7}")
    for tid in tax_ids:
        e = per_entry[tid]
        info = e["info"]
        kdisp = "  n/a" if e["kappa"] is None else f"{e['kappa']:>7.3f}"
        print(f"  {tid:<14}  {e['category']:<22}  {kdisp}  "
              f"{info['prev_a']:>7.3f}  {info['prev_b']:>7.3f}")

    print(f"\nFull results: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
