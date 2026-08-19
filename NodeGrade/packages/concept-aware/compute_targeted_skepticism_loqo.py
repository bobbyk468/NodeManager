#!/usr/bin/env python3
"""
compute_targeted_skepticism_loqo.py -- attempted exact reproduction of the
"MAE 0.4142->0.4220, p=0.094" targeted-skepticism-vs-zero-shot comparison
documented in REPRODUCIBILITY.md Finding 6 / docs/INVESTIGATION_REPORT_2026-08-18.md
Section 5.13, using this project's own established LOQO recalibration
protocol (see compute_pipeline_diagnostic_stepwise.py, compute_clustered_
significance.py: leave-one-question-out, intercept+scale via Ridge, nested
alpha selection on the training folds only).

Why this script exists (2026-08-19, third/fourth review rounds): a
second-review pass found that verify_investigation_integrity.py's
recomputation of this comparison on RAW (uncalibrated) scores gave
p=0.0155, on the wrong basis (not LOQO-recalibrated). No saved script
reproduced the documented 0.4142/0.4220/p=0.094/p=0.39 numbers -- this
is a REPRODUCIBILITY REPAIR (writing down code that recovers a result
the report had already disclosed correctly), not the discovery of a new
methodological gap: REPRODUCIBILITY.md's Finding 6 and docs/
INVESTIGATION_REPORT_2026-08-18.md Section 5.13 both already reported
response-level p=0.094 AND question-clustered p=0.39 side by side before
this script existed. This script just makes that specific recomputation
runnable and checkable against exact expected values, using the SAME
LOQO-recalibration methodology already established elsewhere in this
codebase, run against the same cached data
(data/mohler_real_eval_results.json, data/mohler_real_verifier_targeted.json).

The check below requires BOTH the response-level AND question-clustered
p-values to match their specific documented values (0.09446 / 0.38559)
to a tight tolerance (MAE +/-0.0001, p +/-0.001) -- not either-or, and
not the looser +/-0.01/+/-0.02 tolerances an earlier version of this
script used. Verdict is printed and written to
data/targeted_skepticism_loqo_result.json. If the reproduced numbers do
not match to this tolerance, treat p=0.094 (and the "0.4142->0.4220" MAE
pair) as UNREPRODUCIBLE and retract them -- do not keep citing an
unreproducible statistic. See REPRODUCIBILITY.md Finding 6 for the
retraction record.

Run:
    python3 compute_targeted_skepticism_loqo.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).parent
DATA = BASE / "data"
ALPHA_GRID = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]

# Documented values this script is trying to reproduce (REPRODUCIBILITY.md
# Finding 6 / docs/INVESTIGATION_REPORT_2026-08-18.md Section 5.13: "MAE
# 0.4142->0.4220 ... response-level p=0.094 ... question-clustered p=0.39
# (21/46)"). Both p-values were already disclosed in the original report;
# this script reproduces both, to the precision this LOQO protocol
# actually produces (2026-08-19, fourth review round -- tightened from
# +/-0.01 MAE / +/-0.02 p, and from an either-response-or-clustered OR
# check to requiring both specific values).
DOCUMENTED_MAE_ZS = 0.4142
DOCUMENTED_MAE_TGT = 0.4220
DOCUMENTED_P_RESPONSE = 0.09446
DOCUMENTED_P_CLUSTERED = 0.38559
TOLERANCE_MAE = 0.0001
TOLERANCE_P = 0.001


def inner_select_alpha(X_train, y_train, groups_train) -> float:
    inner_qs = np.unique(groups_train)
    best_alpha, best_mae = ALPHA_GRID[0], float("inf")
    for alpha in ALPHA_GRID:
        errs = []
        for q in inner_qs:
            tr = groups_train != q
            te = groups_train == q
            if tr.sum() < 5 or te.sum() == 0:
                continue
            sc = StandardScaler().fit(X_train[tr])
            m = Ridge(alpha=alpha).fit(sc.transform(X_train[tr]), y_train[tr])
            p = m.predict(sc.transform(X_train[te]))
            errs.append(np.abs(y_train[te] - p))
        if errs:
            mae = np.concatenate(errs).mean()
            if mae < best_mae:
                best_mae, best_alpha = mae, alpha
    return best_alpha


def loqo_predict(X: np.ndarray, y: np.ndarray, qids: np.ndarray) -> np.ndarray:
    unique_qs = np.unique(qids)
    preds = np.zeros(len(y))
    for q in unique_qs:
        te = qids == q
        tr = ~te
        alpha = inner_select_alpha(X[tr], y[tr], qids[tr])
        sc = StandardScaler().fit(X[tr])
        m = Ridge(alpha=alpha).fit(sc.transform(X[tr]), y[tr])
        preds[te] = m.predict(sc.transform(X[te]))
    return np.clip(preds, 0.0, 5.0)


def main() -> int:
    targeted = json.loads((DATA / "mohler_real_verifier_targeted.json").read_text())
    d = json.loads((DATA / "mohler_real_eval_results.json").read_text())

    human, zs, tgt, qids = [], [], [], []
    for r in d["results"]:
        sid = r["id"]
        if sid not in targeted:
            continue
        human.append(r["human_score"])
        zs.append(r["cllm_score"])
        tgt.append(targeted[sid])
        qids.append(r["qid"])
    human = np.array(human)
    zs = np.array(zs)
    tgt = np.array(tgt)
    qids = np.array(qids)
    n, n_q = len(human), len(np.unique(qids))
    print(f"n={n} responses, n_questions={n_q}")

    # LOQO-recalibrated (intercept + scale, nested Ridge alpha), same
    # protocol as compute_pipeline_diagnostic_stepwise.py / compute_
    # clustered_significance.py -- fit on 0-5 raw scale.
    pred_zs = loqo_predict(zs.reshape(-1, 1), human, qids)
    pred_tgt = loqo_predict(tgt.reshape(-1, 1), human, qids)
    mae_zs = float(np.abs(human - pred_zs).mean())
    mae_tgt = float(np.abs(human - pred_tgt).mean())

    diff = np.abs(human - pred_zs) - np.abs(human - pred_tgt)
    _, p_response = wilcoxon(diff, zero_method="wilcox")

    # Question-clustered version (mean per question first), matching the
    # "question-clustered" framing this project uses elsewhere for its
    # primary statistic.
    by_q = defaultdict(lambda: {"zs": [], "tgt": []})
    for i, q in enumerate(qids):
        by_q[q]["zs"].append(diff[i])
    q_diff_means = np.array([np.mean(v["zs"]) for v in by_q.values()])
    _, p_clustered = wilcoxon(q_diff_means, zero_method="wilcox")

    print(f"\nLOQO-recalibrated (0-5 scale): MAE zero-shot={mae_zs:.4f}  MAE targeted={mae_tgt:.4f}")
    print(f"Response-level Wilcoxon p={p_response:.4f}")
    print(f"Question-clustered Wilcoxon p={p_clustered:.4f}")

    mae_zs_matches = bool(abs(mae_zs - DOCUMENTED_MAE_ZS) < TOLERANCE_MAE)
    mae_tgt_matches = bool(abs(mae_tgt - DOCUMENTED_MAE_TGT) < TOLERANCE_MAE)
    p_response_matches = bool(abs(p_response - DOCUMENTED_P_RESPONSE) < TOLERANCE_P)
    p_clustered_matches = bool(abs(p_clustered - DOCUMENTED_P_CLUSTERED) < TOLERANCE_P)
    reproduced = bool(mae_zs_matches and mae_tgt_matches and p_response_matches and p_clustered_matches)

    print(
        f"\nDocumented: MAE zero-shot={DOCUMENTED_MAE_ZS} MAE targeted={DOCUMENTED_MAE_TGT} "
        f"p_response={DOCUMENTED_P_RESPONSE} p_clustered={DOCUMENTED_P_CLUSTERED}"
    )
    print(f"Reproduced within tolerance (MAE +/-{TOLERANCE_MAE}, p +/-{TOLERANCE_P}, BOTH p-values required)? {reproduced}")
    if not reproduced:
        print(
            f"  mae_zs_matches={mae_zs_matches} mae_tgt_matches={mae_tgt_matches} "
            f"p_response_matches={p_response_matches} p_clustered_matches={p_clustered_matches}"
        )
    if not reproduced:
        print(
            "\nVERDICT: NOT REPRODUCED. This project's own established LOQO-"
            "recalibration protocol, applied to the same cached data, does "
            "not recover the documented 0.4142/0.4220/p=0.094 figures. Per "
            "explicit instruction, this statistic must be treated as "
            "UNREPRODUCIBLE and retracted from REPRODUCIBILITY.md and the "
            "investigation report -- not kept with a loosened tolerance or "
            "an alpha-guard workaround."
        )

    out = {
        "n": n, "n_questions": n_q,
        "loqo_recalibrated_mae_zeroshot": float(mae_zs),
        "loqo_recalibrated_mae_targeted": float(mae_tgt),
        "wilcoxon_p_response_level": float(p_response),
        "wilcoxon_p_question_clustered": float(p_clustered),
        "documented_mae_zeroshot": DOCUMENTED_MAE_ZS,
        "documented_mae_targeted": DOCUMENTED_MAE_TGT,
        "documented_p_response": DOCUMENTED_P_RESPONSE,
        "documented_p_clustered": DOCUMENTED_P_CLUSTERED,
        "reproduced_within_tolerance": reproduced,
    }
    out_path = DATA / "targeted_skepticism_loqo_result.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {out_path}")
    return 0 if reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
