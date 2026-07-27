#!/usr/bin/env python3
"""
smoke_run_mohler.py — 5-sample end-to-end pipeline smoke test on Mohler.

Verifies the full ConceptGradePipeline still runs after this session's edits.
Does NOT replace cached n=120 results — those remain authoritative for the
paper. This is a regression sanity check on the live Gemini API path.

Output: data/smoke_5_results.json (5 samples × {pipeline grade, components, human})
Exit code: 0 on success, non-zero if pipeline fails.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

# Pull GEMINI_API_KEY from the backend .env (single source of truth)
ENV_PATH = BASE.parent / "backend" / ".env"
if "GEMINI_API_KEY" not in os.environ and ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip()
            break

if "GEMINI_API_KEY" not in os.environ:
    print("ERROR: GEMINI_API_KEY not in env and not in backend/.env", file=sys.stderr)
    sys.exit(2)

from datasets.mohler_loader import load_mohler_sample
from conceptgrade.pipeline import ConceptGradePipeline


def main() -> int:
    print("[smoke] Loading Mohler sample dataset (10 questions × 12 responses = 120)…")
    dataset = load_mohler_sample()

    # Take 5 samples spanning multiple questions (deterministic: first sample of
    # questions Q1..Q5) so we exercise the pipeline on varied content.
    chosen = []
    seen_qs: set[str] = set()
    for s in dataset.samples:
        if s.question_id not in seen_qs:
            chosen.append(s)
            seen_qs.add(s.question_id)
        if len(chosen) == 5:
            break
    print(f"[smoke] Selected {len(chosen)} samples from questions: "
          f"{[s.question_id for s in chosen]}")

    print("[smoke] Initialising ConceptGradePipeline (gemini-2.5-flash)…")
    pipe = ConceptGradePipeline(
        api_key=os.environ["GEMINI_API_KEY"],
        model="gemini-2.5-flash",
        use_self_consistency=False,        # smoke = single shot
        use_confidence_weighting=True,
        use_llm_verifier=False,            # skip verifier for speed
        sc_inter_run_delay=0.5,
    )

    results = []
    t0 = time.time()
    for i, s in enumerate(chosen, 1):
        t_s = time.time()
        try:
            assessment = pipe.assess_student(
                student_id=f"smoke_{s.question_id}",
                question=s.question,
                answer=s.student_answer,
                reference_answer=s.reference_answer,
            )
            overall_5 = round(assessment.overall_score * 5.0, 2)
            comp = assessment.comparison.get("scores", {})
            results.append({
                "i": i,
                "question_id": s.question_id,
                "human_score": s.score_avg,
                "pipeline_score_0_5": overall_5,
                "abs_error": abs(s.score_avg - overall_5),
                "concept_coverage": round(comp.get("concept_coverage", 0), 4),
                "relationship_accuracy": round(comp.get("relationship_accuracy", 0), 4),
                "latency_sec": round(time.time() - t_s, 2),
                "ok": True,
            })
            print(f"[smoke] {i}/5 {s.question_id}: human={s.score_avg:.2f} "
                  f"pipeline={overall_5:.2f} err={abs(s.score_avg-overall_5):.2f} "
                  f"({results[-1]['latency_sec']}s)")
        except Exception as exc:
            results.append({
                "i": i,
                "question_id": s.question_id,
                "ok": False,
                "error": str(exc)[:300],
            })
            print(f"[smoke] {i}/5 {s.question_id}: FAILED — {exc}", file=sys.stderr)

    out_path = BASE / "data" / "smoke_5_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "n_attempted": len(chosen),
        "n_ok": sum(1 for r in results if r.get("ok")),
        "n_failed": sum(1 for r in results if not r.get("ok")),
        "total_seconds": round(time.time() - t0, 2),
        "mean_abs_error": round(
            sum(r.get("abs_error", 0) for r in results if r.get("ok"))
            / max(1, sum(1 for r in results if r.get("ok"))),
            3,
        ),
        "results": results,
    }
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\n[smoke] Done in {summary['total_seconds']}s "
          f"({summary['n_ok']}/{summary['n_attempted']} ok). "
          f"Mean |err| = {summary['mean_abs_error']}.")
    print(f"[smoke] Results: {out_path}")

    return 0 if summary["n_ok"] == summary["n_attempted"] else 1


if __name__ == "__main__":
    sys.exit(main())
