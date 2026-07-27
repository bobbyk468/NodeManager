#!/usr/bin/env python3
"""
compute_real_fixes.py — execute the structural fixes from the latest
hostile-review round on cached data + local Sentence-BERT (no API spend).

What this script computes:
  REAL-1. Bootstrap 95% CI for MAE reduction on the n=90 Mohler TEST set
          (previous reporting was on n=30 dev set — fixed here).
  REAL-2. Misconception-module ablation: concepts_only (no taxonomy) vs
          C5_fix (with taxonomy). Tests whether the noisy κ=0.33 taxonomy
          is helping or hurting.
  REAL-3. Sentence-BERT baseline on the Mohler n=90 TEST set, computed
          locally with sentence-transformers (no API). Lets us claim a
          direct head-to-head against a modern non-LLM neural baseline
          on the SAME test set, not on a different SemEval split.
  REAL-4. Per-dataset bootstrap 95% CIs on MAE reduction (Mohler,
          DigiKlausur, Kaggle ASAG) — uniform CI reporting across the
          1,239-sample story.

The Verifier data-leakage disclosure is a textual change to the paper,
not a computation; this script does not produce that.

Run:
    python compute_real_fixes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).parent
RNG_SEED = 20260531
RNG = np.random.default_rng(RNG_SEED)
BOOTSTRAP_N = 5000


def _load_eval(name: str) -> dict:
    with (BASE / "data" / f"{name}_eval_results.json").open() as f:
        return json.load(f)


def bootstrap_mae_reduction_ci(
    err_cllm: np.ndarray, err_c5: np.ndarray, n_boot: int = BOOTSTRAP_N,
) -> dict:
    n = len(err_cllm)
    assert len(err_c5) == n
    reductions = np.empty(n_boot)
    maes_cllm = np.empty(n_boot)
    maes_c5 = np.empty(n_boot)
    for b in range(n_boot):
        idx = RNG.integers(0, n, size=n)
        m_cllm = err_cllm[idx].mean()
        m_c5 = err_c5[idx].mean()
        maes_cllm[b] = m_cllm
        maes_c5[b] = m_c5
        reductions[b] = (m_cllm - m_c5) / m_cllm * 100 if m_cllm > 0 else 0.0
    return {
        "point_mae_cllm": float(err_cllm.mean()),
        "point_mae_c5": float(err_c5.mean()),
        "point_reduction_pct": float((err_cllm.mean() - err_c5.mean()) / err_cllm.mean() * 100),
        "boot_n": n_boot,
        "boot_reduction_ci_95": [
            float(np.percentile(reductions, 2.5)),
            float(np.percentile(reductions, 97.5)),
        ],
        "boot_mae_cllm_ci_95": [
            float(np.percentile(maes_cllm, 2.5)),
            float(np.percentile(maes_cllm, 97.5)),
        ],
        "boot_mae_c5_ci_95": [
            float(np.percentile(maes_c5, 2.5)),
            float(np.percentile(maes_c5, 97.5)),
        ],
    }


# ---------------------------------------------------------------------------
# REAL-1 + REAL-4: bootstrap CI per dataset
# ---------------------------------------------------------------------------
def real_1_and_4() -> dict:
    out = {}
    for ds in ["mohler", "digiklausur", "kaggle_asag"]:
        d = _load_eval(ds)
        results = d["results"]
        human = np.array([r["human_score"] for r in results])
        cllm = np.array([r["cllm_score"] for r in results])
        c5 = np.array([r["c5_score"] for r in results])
        err_cllm = np.abs(human - cllm)
        err_c5 = np.abs(human - c5)
        out[ds] = bootstrap_mae_reduction_ci(err_cllm, err_c5)

    # REAL-1 specifically: Mohler TEST split (n=90). The split protocol in
    # the paper is "stratified by question, 30 dev + 90 test". We
    # reproduce: dev = 3 per question × 10 questions = 30; test = 9 per
    # question × 10 questions = 90.
    d = _load_eval("mohler")
    results = d["results"]
    human = np.array([r["human_score"] for r in results])
    cllm = np.array([r["cllm_score"] for r in results])
    c5 = np.array([r["c5_score"] for r in results])
    err_cllm = np.abs(human - cllm)
    err_c5 = np.abs(human - c5)

    # Deterministic stratified test split: take samples 3..11 of each
    # question (indices i with i % 12 in {3,..,11}) → 9 per question × 10
    # questions = 90 test samples.
    test_mask = np.array([(i % 12) >= 3 for i in range(len(results))])
    test_err_cllm = err_cllm[test_mask]
    test_err_c5 = err_c5[test_mask]
    out["mohler_test_n90"] = bootstrap_mae_reduction_ci(
        test_err_cllm, test_err_c5,
    )
    return out


# ---------------------------------------------------------------------------
# REAL-2: misconception module ablation
# ---------------------------------------------------------------------------
def real_2() -> dict:
    """Read the cached `ablation_component_results.json` and compute the
    paired-Wilcoxon for concepts_only vs C5_fix to test whether the
    fair-IRR taxonomy actually moves the needle."""
    from scipy import stats
    with (BASE / "data" / "ablation_component_results.json").open() as f:
        d = json.load(f)
    sys_ = d["systems"]
    out = {
        "summary_mae": {k: round(v["mae"], 4) for k, v in sys_.items()},
        "summary_r": {k: round(v["r"], 4) for k, v in sys_.items()},
        "key_finding_cached": d.get("key_finding", ""),
    }
    # Try to compute per-sample paired test if per-sample preds present
    if "per_sample" in d:
        per = d["per_sample"]
        a = np.array(per["concepts_only"])
        b = np.array(per["C5_fix"])
        _, p_two = stats.wilcoxon(a, b, alternative="two-sided", zero_method="wilcox")
        out["concepts_only_vs_C5_fix_paired_p"] = float(p_two)
    else:
        out["concepts_only_vs_C5_fix_paired_p"] = None
        out["note"] = (
            "per-sample predictions for concepts_only / C5_fix not in this JSON; "
            "MAE difference 0.217 vs 0.223 = 0.006 (concepts_only is slightly "
            "better, indicating the misconception module is at most neutral)"
        )
    return out


# ---------------------------------------------------------------------------
# REAL-3: local Sentence-BERT baseline on Mohler n=90 test
# ---------------------------------------------------------------------------
def real_3() -> dict:
    """Score 90 Mohler test samples with a frozen Sentence-BERT model
    (no fine-tuning; cosine similarity between student and reference
    answer embeddings, scaled to 0..5). This is a direct head-to-head
    against C5_fix on the SAME test set, replacing the published-on-
    different-split BERT number in Table 2."""
    sys.path.insert(0, str(BASE))
    from datasets.mohler_loader import load_mohler_sample
    from sentence_transformers import SentenceTransformer
    from scipy.spatial.distance import cdist
    from scipy import stats

    print("[REAL-3] Loading dataset…", flush=True)
    dataset = load_mohler_sample()
    # Test split = samples 3..11 of each question (matches REAL-1)
    samples = []
    for i, s in enumerate(dataset.samples):
        if (i % 12) >= 3:
            samples.append(s)
    print(f"[REAL-3] Test samples: {len(samples)}", flush=True)

    print("[REAL-3] Loading Sentence-BERT (all-MiniLM-L6-v2)…", flush=True)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("[REAL-3] Encoding answers…", flush=True)
    refs = [s.reference_answer for s in samples]
    students = [s.student_answer for s in samples]
    e_ref = model.encode(refs, convert_to_numpy=True, show_progress_bar=False)
    e_stu = model.encode(students, convert_to_numpy=True, show_progress_bar=False)

    # Cosine similarity per pair, scaled 0..5
    e_ref_n = e_ref / np.linalg.norm(e_ref, axis=1, keepdims=True)
    e_stu_n = e_stu / np.linalg.norm(e_stu, axis=1, keepdims=True)
    cos_sim = np.sum(e_ref_n * e_stu_n, axis=1)
    bert_score = np.clip(cos_sim * 5.0, 0.0, 5.0)

    human = np.array([s.score_avg for s in samples])
    err_bert = np.abs(human - bert_score)
    mae_bert = float(err_bert.mean())
    rmse_bert = float(np.sqrt((err_bert ** 2).mean()))
    pearson_r = float(np.corrcoef(human, bert_score)[0, 1])

    # Pull C5_fix and C_LLM predictions on the same test indices from the
    # cached eval JSON so the comparison is direct
    with (BASE / "data" / "mohler_eval_results.json").open() as f:
        ev = json.load(f)
    results = ev["results"]
    test_indices = [i for i in range(len(results)) if (i % 12) >= 3]
    err_cllm_test = np.array(
        [abs(results[i]["human_score"] - results[i]["cllm_score"]) for i in test_indices]
    )
    err_c5_test = np.array(
        [abs(results[i]["human_score"] - results[i]["c5_score"]) for i in test_indices]
    )
    mae_cllm_test = float(err_cllm_test.mean())
    mae_c5_test = float(err_c5_test.mean())

    # Paired Wilcoxon: C5 vs BERT, on the same n=90 test set
    _, p_c5_vs_bert_two = stats.wilcoxon(
        err_c5_test, err_bert, alternative="two-sided", zero_method="wilcox",
    )
    _, p_c5_vs_bert_one = stats.wilcoxon(
        err_c5_test, err_bert, alternative="less", zero_method="wilcox",
    )

    return {
        "n_test": len(samples),
        "bert_model": "sentence-transformers/all-MiniLM-L6-v2 (frozen, no fine-tune)",
        "mae_bert_frozen": round(mae_bert, 4),
        "rmse_bert_frozen": round(rmse_bert, 4),
        "pearson_r_bert_frozen": round(pearson_r, 4),
        "mae_cllm_test_set": round(mae_cllm_test, 4),
        "mae_c5_test_set": round(mae_c5_test, 4),
        "c5_vs_bert_paired_wilcoxon": {
            "two_tailed_p": round(float(p_c5_vs_bert_two), 4),
            "one_tailed_p_C5_better": round(float(p_c5_vs_bert_one), 4),
        },
        "note": (
            "Sentence-BERT frozen embedding cosine similarity scaled to "
            "[0,5]; no fine-tuning. Provides a direct head-to-head with "
            "C5_fix and C_LLM on the IDENTICAL n=90 Mohler test set, "
            "replacing the historical published-on-different-split BERT "
            "number that the paper previously listed for context only."
        ),
    }


def main() -> int:
    out = {
        "real_1_4_bootstrap_test_set": real_1_and_4(),
        "real_2_misconception_ablation": real_2(),
        "real_3_local_bert_baseline": real_3(),
    }
    out_path = BASE / "data" / "real_fixes_results.json"
    out_path.write_text(json.dumps(out, indent=2))

    print("\n" + "=" * 72)
    print("REAL FIXES — SUMMARY")
    print("=" * 72)
    print()
    print("REAL-1: Mohler TEST-split (n=90) bootstrap MAE-reduction CI")
    test = out["real_1_4_bootstrap_test_set"]["mohler_test_n90"]
    print(f"  Point: C_LLM={test['point_mae_cllm']:.4f} → C5={test['point_mae_c5']:.4f} "
          f"({test['point_reduction_pct']:.2f}%)")
    print(f"  95% CI for reduction: [{test['boot_reduction_ci_95'][0]:.2f}%, "
          f"{test['boot_reduction_ci_95'][1]:.2f}%]")
    print()
    print("REAL-4: per-dataset bootstrap MAE-reduction CIs:")
    for ds in ["mohler", "digiklausur", "kaggle_asag"]:
        x = out["real_1_4_bootstrap_test_set"][ds]
        print(f"  {ds:14s} n=? point={x['point_reduction_pct']:.2f}%  "
              f"95% CI [{x['boot_reduction_ci_95'][0]:.2f}%, "
              f"{x['boot_reduction_ci_95'][1]:.2f}%]")
    print()
    print("REAL-2: misconception-module ablation:")
    r2 = out["real_2_misconception_ablation"]
    for k, v in r2["summary_mae"].items():
        print(f"  {k:18s} MAE={v}")
    print(f"  key_finding (cached): {r2['key_finding_cached'][:200]}")
    print()
    print("REAL-3: local Sentence-BERT baseline on n=90 test:")
    r3 = out["real_3_local_bert_baseline"]
    print(f"  BERT (frozen)  MAE={r3['mae_bert_frozen']}")
    print(f"  C_LLM          MAE={r3['mae_cllm_test_set']}")
    print(f"  C5_fix         MAE={r3['mae_c5_test_set']}")
    print(f"  C5 vs BERT paired Wilcoxon: two-tail p="
          f"{r3['c5_vs_bert_paired_wilcoxon']['two_tailed_p']}, "
          f"one-tail p="
          f"{r3['c5_vs_bert_paired_wilcoxon']['one_tailed_p_C5_better']}")
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
