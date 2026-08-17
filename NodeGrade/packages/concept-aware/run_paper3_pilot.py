#!/usr/bin/env python3
"""
run_paper3_pilot.py — runs the Paper 3 long-answer pilot set through the
REAL LongAnswerPipeline (conceptgrade/lag_pipeline.py) and saves raw,
unedited results.

Methodology discipline (the exact thing the retracted LAG evaluation
violated): this config is fixed BEFORE looking at any result, and is not
touched afterward. If results look bad, that gets reported as-is — the
prompt/config is not tuned against this set. See REPRODUCIBILITY.md,
"CRITICAL: the LAG (long-answer) evaluation is retracted."

Config (fixed, disclosed):
  model          = gemini-2.5-flash        (matches rest of this project)
  use_sure       = True                    (3-persona uncertainty check)
  use_cross_para = True                    (cross-paragraph integration)
  verifier prompt = whatever is CURRENTLY in verifier.py's mode='lag'
                    branch (the one calibrated on the now-retracted
                    benchmark) — reused as-is, not re-tuned. This run
                    evaluates that prompt on genuinely new, held-out data;
                    it does not re-validate it against the data it was
                    tuned on.

Usage:
  export GEMINI_API_KEY="..."   # or sourced from packages/backend/.env
  python run_paper3_pilot.py
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = Path(__file__).parent
MODEL = "gemini-2.5-flash"
USE_SURE = True
USE_CROSS_PARA = True


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY", file=sys.stderr)
        return 1

    pilot = json.loads((BASE / "data" / "paper3_longanswer" / "pilot_set_v1.json").read_text())
    samples = pilot["samples"]

    from knowledge_graph.ds_knowledge_graph import build_data_structures_graph
    from conceptgrade.lag_pipeline import LongAnswerPipeline

    domain_graph = build_data_structures_graph()

    def log(stage, detail):
        print(f"  [{stage}] {detail}")

    pipeline = LongAnswerPipeline(
        api_key=api_key,
        model=MODEL,
        domain_graph=domain_graph,
        use_sure=USE_SURE,
        use_cross_para=USE_CROSS_PARA,
        on_progress=log,
    )

    results = []
    t0 = time.time()
    for i, item in enumerate(samples, 1):
        print(f"\n=== [{i}/{len(samples)}] {item['id']} ({item['word_count']}w, target={item['author_intended_score_0to5']}) ===")
        r = pipeline.assess(
            question=item["question"],
            student_answer=item["student_answer"],
            student_id=item["id"],
        )
        d = r.to_dict()
        d["_pilot_meta"] = {
            "id": item["id"],
            "topic": item["topic"],
            "author_intended_tier": item["author_intended_tier"],
            "author_intended_score_0to5": item["author_intended_score_0to5"],
            "designed_misconception": item["designed_misconception"],
            "word_count": item["word_count"],
        }
        results.append(d)
        print(f"  -> final_score={d['aggregated']['final_score']}/5  "
              f"misconceptions={len(d['aggregated']['misconceptions'])}  "
              f"segments={d['segmentation']['n_segments']}")

    elapsed = time.time() - t0

    out = {
        "meta": {
            "framework": "ConceptGrade LongAnswerPipeline — Paper 3 pilot",
            "model": MODEL,
            "use_sure": USE_SURE,
            "use_cross_para": USE_CROSS_PARA,
            "n_samples": len(samples),
            "total_elapsed_seconds": round(elapsed, 2),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "note": "Config fixed before running; not tuned against this set. "
                    "See REPRODUCIBILITY.md for the retracted prior LAG evaluation "
                    "this replaces.",
        },
        "results": results,
    }

    out_path = BASE / "data" / "paper3_longanswer" / "pilot_run_v1_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote {out_path}")
    print(f"Total elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
