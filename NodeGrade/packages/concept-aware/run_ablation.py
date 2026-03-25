"""
ConceptGrade Ablation Study.

Measures the marginal contribution of each scoring component by
removing one component at a time and comparing against the full model.

Components ablated:
  1. Full ConceptGrade (all components)  <- reference
  2. -Concept Coverage  (coverage = 0)
  3. -Depth/Bloom's     (depth_score = 0)
  4. -SOLO proxy        (solo_approx = 0)
  5. -Accuracy/Misc     (accuracy fixed = 1.0)
  6. -Cosine Similarity (base_sim = 0)
  7. Cosine-Only        (only base_sim)

Usage:
    cd NodeGrade/packages/concept-aware
    python3 run_ablation.py

Output:
    data/ablation_results.json
    data/ablation_summary.txt
"""

import json, os, sys
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datasets.mohler_loader import load_mohler_sample, MohlerSample
from evaluation.metrics import (
    evaluate_grading, add_bootstrap_cis,
    wilcoxon_significance, format_comparison_table,
    format_significance_table,
)

CONCEPT_KEYWORDS = {
    "linked list": ["linked list","node","pointer","head","tail","traversal","insertion","deletion","o(1)","o(n)","linear"],
    "arrays": ["array","contiguous","index","random access","shifting","o(1)","o(n)","memory","insertion"],
    "stack": ["stack","lifo","last in first out","push","pop","peek","o(1)","undo","recursion","backtrack"],
    "binary search tree": ["bst","binary search tree","binary tree","left subtree","right subtree","o(log n)","balanced","skewed","degenerate","ordering","search"],
    "bfs": ["bfs","breadth","queue","level","shortest path","neighbor"],
    "dfs": ["dfs","depth","stack","recursion","backtrack","topological","cycle detection"],
    "hash table": ["hash","hash function","hash table","collision","chaining","open addressing","probing","bucket","o(1)","key","value"],
}
DEPTH_INDICATORS = {
    "because":0.15,"therefore":0.15,"since":0.10,"however":0.12,"although":0.10,"while":0.08,
    "for example":0.15,"such as":0.10,"e.g.":0.10,"compared to":0.12,"in contrast":0.12,
    "unlike":0.10,"worst case":0.15,"best case":0.12,"average case":0.12,
    "complexity":0.10,"o(":0.15,"time complexity":0.15,"space complexity":0.12,
}
MISC_PATTERNS = [
    ("linked list","o(1)","access"),("always o(1)","hash"),
    ("first in first out","stack"),("always o(log n)","bst"),
    ("stack","bfs"),("queue","dfs"),
]

def extract_components(sample):
    answer = sample.student_answer.lower()
    reference = sample.reference_answer.lower()
    try:
        vec = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1,3), max_features=5000)
        tfidf = vec.fit_transform([reference, answer])
        base_sim = float(sk_cosine(tfidf[0:1], tfidf[1:2])[0][0])
    except:
        base_sim = 0.0
    relevant = set()
    for topic, kws in CONCEPT_KEYWORDS.items():
        if any(kw in sample.question.lower() for kw in [topic]+kws[:2]):
            relevant.update(kws)
    if not relevant:
        relevant = set(reference.split())
    found = sum(1 for c in relevant if c in answer)
    concept_coverage = min(1.0, found / max(len(relevant)*0.6, 1))
    depth_score = min(1.0, sum(v for k,v in DEPTH_INDICATORS.items() if k in answer))
    sentences = [s.strip() for s in answer.replace(".", ".\n").split("\n") if s.strip()]
    n = len(sentences)
    if n >= 4 and depth_score > 0.3:
        solo_approx = min(1.0, 0.6 + depth_score*0.4)
    elif n >= 3:
        solo_approx = min(0.8, 0.3 + n*0.1 + depth_score*0.2)
    elif n >= 2:
        solo_approx = min(0.5, 0.15 + n*0.1)
    else:
        solo_approx = 0.1
    accuracy = max(0.0, 1.0 - 0.15*sum(all(t in answer for t in m) for m in MISC_PATTERNS))
    completeness = min(1.0, len(answer)/max(len(reference),1))
    return dict(base_sim=base_sim, concept_coverage=concept_coverage,
                depth_score=depth_score, solo_approx=solo_approx,
                accuracy=accuracy, completeness=completeness)

def composite(c, ablation):
    d = dict(c)
    if ablation == "no_coverage": d["concept_coverage"] = 0.0
    elif ablation == "no_depth":  d["depth_score"] = 0.0
    elif ablation == "no_solo":   d["solo_approx"] = 0.0
    elif ablation == "no_acc":    d["accuracy"] = 1.0
    elif ablation == "no_cosine": d["base_sim"] = 0.0
    elif ablation == "cosine_only":
        return round(max(0.0, min(5.0, d["base_sim"]*5.0)), 2)
    score = (d["base_sim"]*0.10 + d["concept_coverage"]*0.25 + d["depth_score"]*0.20
             + d["solo_approx"]*0.20 + d["accuracy"]*0.15 + d["completeness"]*0.10)
    return round(max(0.0, min(5.0, score*5.0)), 2)

def run_ablation():
    print("="*70)
    print("  ConceptGrade Ablation Study")
    print("  Mohler et al. (2011) CS Short Answer Dataset")
    print("="*70); print()

    dataset = load_mohler_sample()
    human_scores = [s.score_avg for s in dataset.samples]
    all_components = [extract_components(s) for s in dataset.samples]
    print(f"Loaded {dataset.num_samples} samples. Extracting components... done.\n")

    ablations = [
        ("full",       "ConceptGrade (Full)"),
        ("no_coverage","  - Concept Coverage"),
        ("no_depth",   "  - Depth / Bloom's"),
        ("no_solo",    "  - SOLO Proxy"),
        ("no_acc",     "  - Misconception Acc."),
        ("no_cosine",  "  - Cosine Similarity"),
        ("cosine_only","Cosine-Only (Baseline)"),
    ]

    eval_results = []
    all_scores = {}
    for key, name in ablations:
        scores = [composite(c, key) for c in all_components]
        ev = evaluate_grading(human_scores, scores, task_name=name)
        add_bootstrap_cis(ev, human_scores, scores)
        eval_results.append(ev)
        all_scores[key] = scores

    print("="*82)
    print("  ABLATION RESULTS")
    print("="*82); print()
    print(format_comparison_table(eval_results)); print()

    full_ev = eval_results[0]
    print(f"{'Component Removed':<35} {'ΔPearson r':<14} {'ΔQWK':<12} {'ΔRMSE':<12} {'Impact'}")
    print("─"*85)
    for (key, name), ev in zip(ablations[1:], eval_results[1:]):
        dr = ev.pearson_r - full_ev.pearson_r
        dq = ev.qwk - full_ev.qwk
        drmse = ev.rmse - full_ev.rmse
        impact = "HIGH" if abs(dr)>0.05 else "MED" if abs(dr)>0.02 else "LOW"
        print(f"  {name.strip('- '):<33} {dr:<+14.4f} {dq:<+12.4f} {drmse:<+12.4f} {impact}")
    print()

    print("─"*70)
    print("  SIGNIFICANCE — Full Model vs Each Ablation (Wilcoxon)")
    print("─"*70)
    sig_tests = []
    for (key, name), ev in zip(ablations[1:], eval_results[1:]):
        t = wilcoxon_significance(human_scores, all_scores["full"], all_scores[key],
                                  "ConceptGrade (Full)", name.strip("- "))
        sig_tests.append(t)
    print(format_significance_table(sig_tests)); print()

    print("─"*70)
    print("  PER-QUESTION PEARSON r (Full ConceptGrade)")
    print("─"*70)
    for qid in sorted(dataset.questions.keys()):
        q_samples = dataset.get_by_question(qid)
        q_human = [s.score_avg for s in q_samples]
        q_idx = [i for i,s in enumerate(dataset.samples) if s.question_id==qid]
        q_full = [all_scores["full"][i] for i in q_idx]
        if len(q_human) >= 3:
            from scipy.stats import pearsonr
            r, p = pearsonr(q_human, q_full)
            q_text = dataset.questions[qid][:55]
            print(f"  Q{qid}: r={r:.4f} (p={p:.4f}) — {q_text}...")
    print()

    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)

    output = {
        "meta": {"study":"ConceptGrade Ablation Study",
                 "dataset":"Mohler et al. (2011) n=30",
                 "timestamp":datetime.now().isoformat()},
        "ablations": {k: {"name":n, "scores":all_scores[k],
                          "metrics":ev.to_dict()}
                      for (k,n), ev in zip(ablations, eval_results)},
        "delta_table": [
            {"ablation":n.strip("- "),
             "delta_pearson_r":round(ev.pearson_r-full_ev.pearson_r,4),
             "delta_qwk":round(ev.qwk-full_ev.qwk,4),
             "delta_rmse":round(ev.rmse-full_ev.rmse,4)}
            for (k,n), ev in zip(ablations[1:], eval_results[1:])
        ],
        "significance_tests": sig_tests,
    }
    rpath = os.path.join(output_dir, "ablation_results.json")
    with open(rpath, "w") as f:
        json.dump(output, f, indent=2)

    spath = os.path.join(output_dir, "ablation_summary.txt")
    lines = ["ConceptGrade Ablation Study", "="*50,
             f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"Dataset: Mohler et al. (2011) — {dataset.num_samples} samples", "",
             "ABLATION TABLE:", format_comparison_table(eval_results), "",
             "DELTA vs FULL MODEL:"]
    for (k,n), ev in zip(ablations[1:], eval_results[1:]):
        dr = ev.pearson_r-full_ev.pearson_r
        dq = ev.qwk-full_ev.qwk
        lines.append(f"  {n.strip('- '):<33} ΔPearson r={dr:+.4f}  ΔQWK={dq:+.4f}")
    lines += ["", "SIGNIFICANCE TESTS:", format_significance_table(sig_tests)]
    with open(spath, "w") as f:
        f.write("\n".join(lines))

    print(f"Results saved to {rpath}")
    print(f"Summary saved to {spath}")
    print("Ablation study complete.")

if __name__ == "__main__":
    run_ablation()
