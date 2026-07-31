#!/usr/bin/env python3
"""
compute_sentence_bert_baseline.py — Frozen Sentence-BERT baselines
(all-MiniLM-L6-v2, all-mpnet-base-v2) on the real, KG-aligned Mohler
sample, replacing the fabricated-fixture-based REAL-3/REAL-5 numbers in
compute_real_fixes.py / compute_real_fixes_v2.py (see REPRODUCIBILITY.md's
"CRITICAL" section).

Motivation
----------
Paper 1's "Direct head-to-head with non-LLM neural baselines" paragraph
was left as an explicit gap after the real-data correction: the old
MiniLM/MPNet numbers were computed against the fabricated 120-sample
fixture's n=90 "test split" (which itself doesn't exist for the real,
un-split, variably-sized 46-question dataset). This is entirely local
embedding inference -- no LLM API calls, no cost -- so there is no reason
to leave it unverified once the real data is available.

Method
------
Encode reference and student answers with each frozen model, cosine
similarity scaled to [0, 5], no fine-tuning. Compared against the
already-cached C_LLM and C5_fix real-data predictions
(data/mohler_real_eval_results.json) on the same n=1,262 sample --
no fabricated-data test-split concept needed, matching how Table 1's
other real-data numbers are reported (full sample, hyperparameters
fixed before real data was used).

Run:
    python3 compute_sentence_bert_baseline.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).parent


def run_model(model_name: str, refs: list[str], students: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    print(f"[SBERT] Loading {model_name}…", flush=True)
    model = SentenceTransformer(model_name)
    print(f"[SBERT] Encoding {len(refs)} pairs…", flush=True)
    e_ref = model.encode(refs, convert_to_numpy=True, show_progress_bar=False)
    e_stu = model.encode(students, convert_to_numpy=True, show_progress_bar=False)
    e_ref_n = e_ref / np.linalg.norm(e_ref, axis=1, keepdims=True)
    e_stu_n = e_stu / np.linalg.norm(e_stu, axis=1, keepdims=True)
    cos_sim = np.sum(e_ref_n * e_stu_n, axis=1)
    return np.clip(cos_sim * 5.0, 0.0, 5.0)


def main() -> int:
    with (BASE / "data" / "mohler_real_eval_results.json").open() as f:
        cached = {r["id"]: r for r in json.load(f)["results"]}
    with (BASE / "data" / "mohler_real" / "mohler_real_kg_aligned.json").open() as f:
        raw = json.load(f)["samples"]

    ids = [r["id"] for r in raw]
    refs = [r["reference_answer"] for r in raw]
    students = [r["student_answer"] for r in raw]
    human = np.array([cached[i]["human_score"] for i in ids])
    cllm = np.array([cached[i]["cllm_score"] for i in ids])
    c5 = np.array([cached[i]["c5_score"] for i in ids])
    err_cllm = np.abs(human - cllm)
    err_c5 = np.abs(human - c5)

    def mae(pred):
        return float(np.mean(np.abs(human - pred)))

    def rmse(pred):
        return float(np.sqrt(np.mean((human - pred) ** 2)))

    print(f"n = {len(ids)}")
    print(f"C_LLM  MAE={mae(cllm):.4f}")
    print(f"C5_fix MAE={mae(c5):.4f}")

    out = {"n": len(ids), "mae_cllm": mae(cllm), "mae_c5": mae(c5), "models": {}}

    for model_name, key in [("all-MiniLM-L6-v2", "minilm"), ("all-mpnet-base-v2", "mpnet")]:
        pred = run_model(model_name, refs, students)
        err_bert = np.abs(human - pred)
        r = float(np.corrcoef(human, pred)[0, 1])
        m, rm = mae(pred), rmse(pred)
        _, p_c5_vs_bert_two = stats.wilcoxon(err_c5, err_bert, alternative="two-sided", zero_method="wilcox")
        _, p_c5_vs_bert_one = stats.wilcoxon(err_c5, err_bert, alternative="less", zero_method="wilcox")
        _, p_cllm_vs_bert_two = stats.wilcoxon(err_cllm, err_bert, alternative="two-sided", zero_method="wilcox")
        print(f"\n{model_name} (frozen, no fine-tune):")
        print(f"  MAE={m:.4f}  RMSE={rm:.4f}  r={r:.4f}")
        print(f"  C5_fix vs {key}: two-tailed p={p_c5_vs_bert_two:.6g}, one-tailed p={p_c5_vs_bert_one:.6g}")
        print(f"  C_LLM vs {key}:  two-tailed p={p_cllm_vs_bert_two:.6g}")
        out["models"][key] = {
            "model": f"sentence-transformers/{model_name} (frozen, no fine-tune)",
            "mae": m, "rmse": rm, "pearson_r": r,
            "c5_vs_bert_p_two_tailed": float(p_c5_vs_bert_two),
            "c5_vs_bert_p_one_tailed": float(p_c5_vs_bert_one),
            "cllm_vs_bert_p_two_tailed": float(p_cllm_vs_bert_two),
        }

    out_path = BASE / "data" / "sentence_bert_baseline_real.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
