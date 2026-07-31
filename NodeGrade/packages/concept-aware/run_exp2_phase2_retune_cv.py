#!/usr/bin/env python3
"""
run_exp2_phase2_retune_cv.py — Phase 2 of Experiment #2 (question-held-out
CV with in-fold retuning, independent review round 4).

Requires data/exp2_raw_signals.json (from run_exp2_phase1_signals.py).

Design
------
Leave-one-question-out CV, 10 folds (Q1..Q10). In each fold:
  1. Grid-search the Layer-1 confidence threshold tau over a candidate set,
     using ONLY the 9 training questions (108 responses). For each tau,
     concepts are re-filtered offline from Phase 1's unfiltered signals and
     re-compared against the frozen v1.0-expert KG via the same
     ConfidenceWeightedComparator the pipeline itself uses (algorithmic, no
     LLM) -- this reproduces exactly what pipeline.py does at that tau.
     The one step that DOES need an LLM call is the verifier judgment,
     since its prompt embeds the tau-dependent concept-coverage lists; all
     108 training responses at one tau are sent as ONE batched call (not
     108 individual calls) by reusing LLMVerifier.build_user_prompt()'s
     exact per-sample prompt logic and concatenating it across samples.
  2. The tau with the lowest training MAE is selected for this fold.
  3. The held-out question's 12 responses are re-filtered/re-compared at
     the selected tau and scored with one more batched verifier call.

This directly answers the round-4 "not fixed" item: whether the
originally-tuned threshold survives when tuning is redone independently
per held-out question, rather than tuned once on a response-level dev
split that overlaps in question-identity with the test set.

Why not also retune kg_weight/w1..w6? Verified by direct code inspection
(see REPRODUCIBILITY.md, 2026-07-27 entry): the evaluated configuration
uses verifier_weight=1.0, under which `final = verified` -- the pre-verifier
kg_score/w1..w6 blend has zero effect on the final score and its numeric
value is never inserted into the verifier's prompt. Only tau changes what
the verifier actually sees. Retuning w1..w6 in this architecture would be
retuning a dead parameter.

Run:
    python3 run_exp2_phase2_retune_cv.py             # run all 10 folds (resumable)
    python3 run_exp2_phase2_retune_cv.py --status
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
SIGNALS_PATH = DATA / "exp2_raw_signals.json"
BATCH_DIR = DATA / "exp2_verifier_batches"
RESULTS_PATH = DATA / "exp2_retune_cv_results.json"

TAU_CANDIDATES = [0.0, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.90]
QUESTIONS = [f"Q{i}" for i in range(1, 11)]


def _load_gemini_key() -> str:
    env_path = BASE.parent / "backend" / ".env"
    with env_path.open() as f:
        for line in f:
            m = re.match(r'^GEMINI_API_KEY=(.*)$', line.strip())
            if m:
                return m.group(1)
    raise RuntimeError(f"GEMINI_API_KEY not found in {env_path}")


def _build_comparator_and_verifier():
    # Import order matters: conceptgrade.pipeline (pulled in transitively by
    # conceptgrade.verifier) must load before graph_comparison.* directly,
    # or graph_comparison.comparator's "from ..knowledge_graph..." relative
    # import hits a partial-init circular-import error.
    from conceptgrade.verifier import LLMVerifier
    from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
    from knowledge_graph.domain_graph import DomainKnowledgeGraph

    with (DATA / "ds_knowledge_graph.json").open() as f:
        kg_data = json.load(f)
    frozen_v1_kg = DomainKnowledgeGraph.from_dict(kg_data)
    assert frozen_v1_kg.num_relationships == 138, (
        f"Expected frozen v1.0-expert KG (138 rel), got {frozen_v1_kg.num_relationships}"
    )
    comparator = ConfidenceWeightedComparator(domain_graph=frozen_v1_kg)
    key = _load_gemini_key()
    verifier = LLMVerifier(api_key=key, model="gemini-2.5-flash", verifier_weight=1.0)
    return comparator, verifier


def filter_and_compare(row: dict, tau: float, comparator) -> dict:
    """Re-filter Phase 1's unfiltered concept graph at `tau` and re-run the
    offline (no-LLM) KG comparator, exactly mirroring pipeline.py's own
    filter-then-compare sequence (conceptgrade/pipeline.py lines ~351-388)."""
    from concept_extraction.extractor import StudentConceptGraph

    raw = row["concept_graph"]
    concepts = raw.get("concepts", [])
    filtered_concepts = [c for c in concepts if c.get("confidence", 0.5) >= tau]
    kept_ids = {c["concept_id"] for c in filtered_concepts}
    relationships = raw.get("relationships", [])
    filtered_relationships = [
        r for r in relationships
        if r.get("source_id") in kept_ids and r.get("target_id") in kept_ids
    ]

    filtered_dict = dict(raw)
    filtered_dict["concepts"] = filtered_concepts
    filtered_dict["relationships"] = filtered_relationships
    student_graph = StudentConceptGraph.from_dict(filtered_dict)

    comparison = comparator.compare(student_graph=student_graph, question=row["question"])
    return comparison.to_dict()


def build_batch_prompt(rows: list[dict], comparisons: list[dict], verifier) -> tuple[str, str]:
    """Combine N samples' verifier prompts (built via the pipeline's own
    LLMVerifier.build_user_prompt, so the per-sample evidence text is
    byte-identical to what a single-sample verify() call would send) into
    ONE batched prompt requesting a JSON dict of results keyed by id."""
    system_prompt = None
    blocks = []
    for row, comparison in zip(rows, comparisons):
        sys_p, user_p, _ = verifier.build_user_prompt(
            question=row["question"],
            student_answer=row["student_answer"],
            comparison_result=comparison,
            blooms=row["blooms"],
            solo=row["solo"],
            misconceptions=row["misconceptions"],
            reference_answer=row["reference_answer"],
            mode="sag",
        )
        system_prompt = sys_p  # identical across all rows (mode="sag" fixed)
        # Strip this sample's own single-sample JSON-instruction footer;
        # the marker text is the stable literal from VERIFIER_USER.
        marker = "\nReturn ONLY valid JSON:"
        idx = user_p.rfind(marker)
        evidence_block = user_p[:idx] if idx != -1 else user_p
        blocks.append(f"=== SAMPLE ID: {row['id']} ===\n{evidence_block}")

    footer = (
        "\n\nFor EACH sample above, independently apply the scoring guide and "
        "grade it on its own merits (do not let one sample's grade anchor another's). "
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "scores": {\n'
        '    "<SAMPLE ID>": {\n'
        '      "verified_score": <float 0.0-5.0 in 0.25 increments>,\n'
        '      "adjustment_direction": "confirm|increase|decrease",\n'
        '      "confidence": 0.0-1.0\n'
        "    },\n"
        "    ...\n"
        "  }\n"
        "}"
    )
    user_prompt = "\n\n".join(blocks) + footer
    return system_prompt, user_prompt


def call_batched_verifier(verifier, system_prompt: str, user_prompt: str, batch_tag: str) -> dict:
    """Issue one live call covering all samples in the prompt; save the raw
    response to data/exp2_verifier_batches/ for reuse/audit. Retries on
    transient network errors (this run has twice hit
    httpcore/httpx.ReadError: Connection reset by peer partway through a
    fold) -- 3 attempts with exponential backoff before giving up."""
    import time
    from conceptgrade.llm_client import parse_llm_json

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = BATCH_DIR / f"{batch_tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    last_exc = None
    for attempt in range(3):
        try:
            response = verifier.client.chat.completions.create(
                model=verifier.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=8192,
            )
            raw_text = response.choices[0].message.content
            parsed = parse_llm_json(raw_text)
            scores = parsed.get("scores", parsed)
            cache_path.write_text(json.dumps({"raw_text": raw_text, "scores": scores}, indent=2))
            return {"raw_text": raw_text, "scores": scores}
        except Exception as e:
            last_exc = e
            wait = 3 * (2 ** attempt)
            print(f"    [retry] {batch_tag} attempt {attempt+1}/3 failed "
                  f"({type(e).__name__}: {e}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"{batch_tag}: failed after 3 retries") from last_exc


CHUNK_SIZE = 30  # keeps each call's output comfortably under the token cap


def score_rows(rows: list[dict], tau: float, comparator, verifier, batch_tag: str) -> dict:
    """Filter+compare all rows at `tau`, batch-verify in chunks of
    CHUNK_SIZE (each chunk = one call, independently cached/resumable),
    return {id: verified_score}."""
    out = {}
    for chunk_i in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[chunk_i: chunk_i + CHUNK_SIZE]
        comparisons = [filter_and_compare(r, tau, comparator) for r in chunk]
        system_prompt, user_prompt = build_batch_prompt(chunk, comparisons, verifier)
        tag = f"{batch_tag}_c{chunk_i // CHUNK_SIZE}"
        result = call_batched_verifier(verifier, system_prompt, user_prompt, tag)
        scores = result["scores"]
        for r in chunk:
            sid = str(r["id"])
            entry = scores.get(sid)
            if entry is None:
                print(f"    [warn] no score returned for sample {sid} (tau={tau}, batch={tag})")
                continue
            raw_score = float(entry["verified_score"]) if isinstance(entry, dict) else float(entry)
            out[sid] = max(0.0, min(5.0, round(raw_score * 4) / 4))
    return out


def mae(rows: list[dict], scores: dict) -> float:
    errs = [abs(r["human_score"] - scores[str(r["id"])]) for r in rows if str(r["id"]) in scores]
    return sum(errs) / len(errs) if errs else float("inf")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if not SIGNALS_PATH.exists():
        print(f"Missing {SIGNALS_PATH} -- run run_exp2_phase1_signals.py first.")
        return 1

    signals = json.loads(SIGNALS_PATH.read_text())
    if len(signals) < 120:
        print(f"Phase 1 incomplete: {len(signals)}/120 signals. "
              f"Run run_exp2_phase1_signals.py to finish, or --status to just check.")
        if not args.status:
            return 1

    for i, row in enumerate(signals):
        row["id"] = row["loader_idx"]

    if args.status:
        done = json.loads(RESULTS_PATH.read_text())["folds"] if RESULTS_PATH.exists() else []
        print(f"Phase 1 signals: {len(signals)}/120")
        print(f"Phase 2 folds complete: {len(done)}/10 ({[d['held_out_qid'] for d in done]})")
        return 0

    comparator, verifier = _build_comparator_and_verifier()

    results = {"folds": []}
    if RESULTS_PATH.exists():
        results = json.loads(RESULTS_PATH.read_text())
    done_qids = {f["held_out_qid"] for f in results["folds"]}

    by_qid: dict[str, list[dict]] = {}
    for row in signals:
        by_qid.setdefault(row["qid"], []).append(row)

    for held_out_q in QUESTIONS:
        if held_out_q in done_qids:
            print(f"[{held_out_q}] already done, skipping")
            continue

        train_rows = [r for q, rs in by_qid.items() if q != held_out_q for r in rs]
        test_rows = by_qid[held_out_q]
        print(f"\n=== Fold held-out={held_out_q}: train n={len(train_rows)}, test n={len(test_rows)} ===")

        tau_maes = {}
        for tau in TAU_CANDIDATES:
            tag = f"{held_out_q}_train_tau{tau}"
            train_scores = score_rows(train_rows, tau, comparator, verifier, tag)
            m = mae(train_rows, train_scores)
            tau_maes[tau] = m
            print(f"  tau={tau:.2f} -> train MAE={m:.4f}")

        best_tau = min(tau_maes, key=tau_maes.get)
        print(f"  -> selected tau={best_tau} (train MAE={tau_maes[best_tau]:.4f})")

        test_tag = f"{held_out_q}_test_tau{best_tau}"
        test_scores = score_rows(test_rows, best_tau, comparator, verifier, test_tag)
        test_mae = mae(test_rows, test_scores)
        print(f"  -> held-out {held_out_q} test MAE={test_mae:.4f} (n={len(test_rows)})")

        results["folds"].append({
            "held_out_qid": held_out_q,
            "tau_grid_train_mae": tau_maes,
            "selected_tau": best_tau,
            "test_mae": test_mae,
            "predictions": [
                {"id": str(r["id"]), "human_score": r["human_score"],
                 "retuned_c5_score": test_scores.get(str(r["id"]))}
                for r in test_rows
            ],
        })
        RESULTS_PATH.write_text(json.dumps(results, indent=2))

    print(f"\nAll folds complete. Results in {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
