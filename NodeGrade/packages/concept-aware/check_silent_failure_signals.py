#!/usr/bin/env python3
"""
check_silent_failure_signals.py — validate the user-study premise
BEFORE any API spend.

Gemini Round 3 raised: "If your 'silent failures' are truly insidious,
it means the pipeline's internal flags (such as KG density or SOLO
scores) look perfectly normal despite the bad grade. If the dashboard
features do not actively betray the error, the educator will look at a
confident 4.5/5.0 score, see clean visual layouts, and blindly click
'Accept.'"

This script checks whether the proposed silent-failure stratum (pipeline
C5 score >= 4.0 AND human <= 2.5) actually has internal signals
(chain_pct, matched_concepts count, SOLO/Bloom proxies) that DIFFER
significantly from the reliable stratum (pipeline within 0.5 of human).

If the silent-failure stratum's internal signals are STATISTICALLY
DISTINGUISHABLE from the reliable stratum, the dashboard has something
real to surface, and the study premise holds.

If they look the same, the dashboard is blind to the failure mode and
the user study is doomed at any sample size.

Run:
    python check_silent_failure_signals.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats

BASE = Path(__file__).parent


def stratify(name: str):
    with (BASE / "data" / f"{name}_eval_results.json").open() as f:
        d = json.load(f)
    results = d["results"]

    reliable = []
    silent_failure = []
    other = []
    for r in results:
        gap = r["c5_score"] - r["human_score"]
        c5 = r["c5_score"]
        human = r["human_score"]
        if abs(gap) <= 0.5:
            reliable.append(r)
        elif c5 >= 4.0 and human <= 2.5:
            silent_failure.append(r)
        else:
            other.append(r)
    return reliable, silent_failure, other, results


def parse_chain_pct(s):
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip().rstrip("%")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def summarise_signals(name: str, group, label: str):
    if not group:
        print(f"  [{label}] empty stratum — cannot summarise")
        return None
    matched_n = [len(r.get("matched_concepts", [])) for r in group]
    chain_pct = [parse_chain_pct(r.get("chain_pct", "0%")) for r in group]
    solo_counts = Counter(r.get("solo", "Unknown") for r in group)
    bloom_counts = Counter(r.get("bloom", "Unknown") for r in group)
    print(f"  [{label}] n = {len(group)}")
    print(f"    matched_concepts: mean = {np.mean(matched_n):.2f}, "
          f"median = {np.median(matched_n):.0f}, max = {max(matched_n)}")
    print(f"    chain_pct:        mean = {np.nanmean(chain_pct):.1f}%, "
          f"median = {np.nanmedian(chain_pct):.0f}%, "
          f"min = {np.nanmin(chain_pct):.0f}%")
    print(f"    SOLO distribution: {dict(solo_counts.most_common(3))}")
    print(f"    Bloom distribution: {dict(bloom_counts.most_common(3))}")
    return {
        "n": len(group),
        "matched_n_mean": float(np.mean(matched_n)),
        "matched_n_median": float(np.median(matched_n)),
        "matched_n_max": int(max(matched_n)),
        "chain_pct_mean": float(np.nanmean(chain_pct)),
        "chain_pct_median": float(np.nanmedian(chain_pct)),
        "solo_dist": dict(solo_counts),
        "bloom_dist": dict(bloom_counts),
        "raw_matched_n": matched_n,
        "raw_chain_pct": chain_pct,
    }


def compare(name: str, reliable, silent_failure):
    """Mann-Whitney U test: do reliable vs silent_failure differ on each signal?"""
    if not reliable or not silent_failure:
        return None
    out = {}
    for signal_name, getter in [
        ("matched_n", lambda r: len(r.get("matched_concepts", []))),
        ("chain_pct", lambda r: parse_chain_pct(r.get("chain_pct", "0%"))),
    ]:
        r_vals = np.array([getter(r) for r in reliable], dtype=float)
        s_vals = np.array([getter(r) for r in silent_failure], dtype=float)
        r_vals = r_vals[~np.isnan(r_vals)]
        s_vals = s_vals[~np.isnan(s_vals)]
        if len(r_vals) < 2 or len(s_vals) < 2:
            out[signal_name] = {"status": "insufficient_data"}
            continue
        try:
            u_stat, p = stats.mannwhitneyu(r_vals, s_vals, alternative="two-sided")
            d_z = (r_vals.mean() - s_vals.mean()) / np.std(
                np.concatenate([r_vals, s_vals]), ddof=1)
        except Exception as e:
            out[signal_name] = {"status": "error", "msg": str(e)}
            continue
        out[signal_name] = {
            "reliable_mean": float(r_vals.mean()),
            "silent_failure_mean": float(s_vals.mean()),
            "mann_whitney_p": float(p),
            "effect_size_d": float(d_z),
            "interpretation": (
                "DISTINGUISHABLE — dashboard premise holds"
                if p < 0.05 else
                "INDISTINGUISHABLE — dashboard premise at risk"
            ),
        }
    return out


def main() -> int:
    print("=" * 72)
    print("SILENT-FAILURE STRATUM VALIDITY CHECK")
    print("=" * 72)
    print("Gemini Round 3: validate the user-study premise before any spend.")
    print("Threshold:  reliable     = |c5 - human| <= 0.5")
    print("            silent-fail  = c5 >= 4.0 AND human <= 2.5")
    print()

    overall = {}
    for name in ["mohler", "digiklausur", "kaggle_asag"]:
        rel, sf, oth, all_ = stratify(name)
        n_rel, n_sf = len(rel), len(sf)
        print(f"\n=== {name.upper()} (total = {len(all_)}) ===")
        print(f"  Reliable stratum:        {n_rel} ({n_rel/len(all_)*100:.1f}%)")
        print(f"  Silent-failure stratum:  {n_sf} ({n_sf/len(all_)*100:.1f}%)")
        print(f"  Other (gap 0.5-1.0, etc): {len(oth)}")
        if n_sf == 0:
            print(f"  ⚠ ZERO silent-failure samples in {name}; cannot validate.")
            overall[name] = {"status": "no_silent_failures"}
            continue
        if n_rel == 0:
            print(f"  ⚠ ZERO reliable samples; cannot compare.")
            overall[name] = {"status": "no_reliable"}
            continue

        print(f"\n  Internal signal summary:")
        rel_sig = summarise_signals(name, rel, "reliable")
        print()
        sf_sig = summarise_signals(name, sf, "silent-fail")
        cmp_ = compare(name, rel, sf)
        if cmp_:
            print(f"\n  Mann-Whitney U on internal signals (two-tailed):")
            for sig, res in cmp_.items():
                if "status" in res:
                    print(f"    {sig}: {res}")
                else:
                    print(f"    {sig}: reliable mean = {res['reliable_mean']:.2f}, "
                          f"silent-fail mean = {res['silent_failure_mean']:.2f}, "
                          f"p = {res['mann_whitney_p']:.4f}, "
                          f"d = {res['effect_size_d']:.3f}")
                    print(f"      → {res['interpretation']}")
        overall[name] = {
            "n_reliable": n_rel,
            "n_silent_failure": n_sf,
            "n_other": len(oth),
            "reliable_signals": {k: v for k, v in (rel_sig or {}).items()
                                  if not k.startswith("raw_")},
            "silent_failure_signals": {k: v for k, v in (sf_sig or {}).items()
                                       if not k.startswith("raw_")},
            "comparison": cmp_,
        }

    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)
    n_distinguishable = 0
    n_total_compared = 0
    for name, res in overall.items():
        cmp_ = res.get("comparison")
        if not cmp_:
            continue
        for sig, sig_res in cmp_.items():
            if "interpretation" not in sig_res:
                continue
            n_total_compared += 1
            if "DISTINGUISHABLE" in sig_res["interpretation"]:
                n_distinguishable += 1
    print(f"Of {n_total_compared} signal x dataset comparisons, "
          f"{n_distinguishable} show statistically distinguishable means "
          f"between reliable and silent-failure strata.")
    if n_total_compared > 0:
        if n_distinguishable / n_total_compared >= 0.5:
            print("→ The dashboard premise HOLDS for at least half the "
                  "signal/dataset combinations. User study is testable.")
        else:
            print("→ The dashboard premise DOES NOT HOLD for the majority "
                  "of signal/dataset combinations. The user study is at "
                  "high risk of a null result, regardless of dashboard design.")
            print("  Per Gemini's overall advice: re-design before any spend.")

    out_path = BASE / "data" / "silent_failure_validity_check.json"
    out_path.write_text(json.dumps(overall, indent=2))
    print(f"\n[saved] {out_path}")
    return 0


if __name__ == "__main__":
    main()
    raise SystemExit(0)
