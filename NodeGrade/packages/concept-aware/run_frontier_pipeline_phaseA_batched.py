#!/usr/bin/env python3
"""
run_frontier_pipeline_phaseA_batched.py -- Phase A of the full-pipeline
frontier-model comparison (Option A: does ConceptGrade's architecture add
value on a stronger backbone than Gemini?).

Produces the same output shape as run_real_eval_phaseA_signals.py
(concept_graph, comparison_result, misconceptions, false_beliefs per
sample), but for an OpenRouter-routed model instead of Gemini, and with
extraction batched (chunked multi-sample calls) instead of one call per
sample -- extraction is 3 self-consistency runs x every sample, always
fires, and is the dominant cost/time driver, so it gets full batching
with the exact same offline majority-vote merge logic as
SelfConsistentExtractor._vote() (verified equivalent, see _vote_batch()
below). Misconception detection (conditional -- only fires when there
are incorrect relationships) and false-belief detection (always fires,
but a small/cheap prompt) are run per-sample but CONCURRENTLY
(ThreadPoolExecutor), reusing MisconceptionDetector/FalseBeliefDetector
unmodified -- deliberately not reimplemented in batched-prompt form,
since that logic (taxonomy matching, severity fallback) is intricate
enough that a subtly-wrong reimplementation is a real risk for no clear
cost benefit (these calls are cheap and conditional/small already).

Output: data/{tag}_pipeline_phaseA_signals.json, same row shape as
mohler_real_phaseA_signals.json.

Run:
    python3 run_frontier_pipeline_phaseA_batched.py --model gpt --pilot 25
    python3 run_frontier_pipeline_phaseA_batched.py --model gpt
    python3 run_frontier_pipeline_phaseA_batched.py --model gpt --status
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"

CHUNK_SIZE = 25
N_RUNS = 3
MIN_VOTES = 2
TEMPERATURES = [0.0, 0.15, 0.25]
EXTRACTION_CONFIDENCE_THRESHOLD = 0.70  # matches the paper's tuned default
# OpenRouter enforces a new-account rate limit of 10 req/min on
# openai/gpt-5.6-terra specifically (discovered via a 429 on this stage's
# first pilot run). MISC_FB_WORKERS controls concurrency; MISC_FB_RPM_CAP
# paces requests so the pool never exceeds that ceiling regardless of
# worker count. Both are model-dependent -- Claude/DeepSeek may not need
# this, but capping unconditionally is harmless (just slower) if they
# don't hit the same limit.
MISC_FB_WORKERS = 8
MISC_FB_RPM_CAP = 9  # stay under the observed 10/min ceiling with margin

# Extraction chunks are independent of each other (different sample subsets,
# no shared state) and were originally run sequentially, one chunk at a time
# -- each large multi-sample completion takes 1-9 min regardless of rate
# limits, so serial execution was the real bottleneck. Parallelized the same
# way as the misc/fb stage, with its own conservative rate cap since we
# haven't stress-tested every model's actual ceiling (only gpt-5.6-terra's
# hard 10/min new-account limit is confirmed; treat others cautiously).
EXTRACTION_WORKERS = 8
EXTRACTION_RPM_CAP = 20

MODELS = {
    "claude":   "anthropic/claude-sonnet-5",
    "gpt":      "openai/gpt-5.6-terra",
    "deepseek": "deepseek/deepseek-chat-v3.1",
}


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield i // size, rows[i:i + size]


def _call_batched(client, model: str, system_prompt: str, user_prompt: str,
                   batch_dir: Path, tag: str, max_tokens: int = 8192) -> dict:
    from conceptgrade.llm_client import parse_llm_json

    batch_dir.mkdir(parents=True, exist_ok=True)
    cache_path = batch_dir / f"{tag}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    last_exc = None
    for attempt in range(3):
        try:
            messages = [{"role": "user", "content": user_prompt}]
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=0.0, max_tokens=max_tokens,
            )
            raw_text = resp.choices[0].message.content
            parsed = parse_llm_json(raw_text)
            cache_path.write_text(json.dumps({"raw_text": raw_text, "parsed": parsed}, indent=2))
            return {"raw_text": raw_text, "parsed": parsed}
        except Exception as e:
            last_exc = e
            wait = 3 * (2 ** attempt)
            print(f"    [retry] {tag} attempt {attempt+1}/3 failed ({type(e).__name__}: {e}); "
                  f"retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"{tag}: failed after 3 retries") from last_exc


# ── Batched extraction (one temperature-run, all samples chunked) ──────────────

EXTRACTION_BATCH_SYSTEM = """You are an expert Computer Science educator analyzing student answers about Data Structures and Algorithms.

Your task is to extract ALL domain concepts mentioned or implied in each student's response, and identify the relationships between them.

IMPORTANT RULES:
1. Extract concepts the student actually demonstrates understanding of (not just mentions in passing)
2. Identify relationships the student explicitly or implicitly establishes between concepts
3. Use ONLY concepts from each sample's provided domain ontology when possible
4. If a student uses informal language, map it to the closest formal concept
5. Capture misconceptions as incorrect relationships (is_correct: false)

Available concept types: data_structure, algorithm, operation, property, complexity_class, design_pattern, abstract_concept, programming_construct
Available relationship types: is_a, has_part, prerequisite_for, implements, uses, variant_of, has_property, has_complexity, operates_on, produces, contrasts_with

Process EACH sample independently -- do not let one sample's answer influence another's grading. Return ONE JSON object covering all samples in the batch."""


def _build_extraction_batch_prompt(batch: list[dict]) -> str:
    """batch: list of {id, question, student_answer, ontology} dicts."""
    blocks = []
    for r in batch:
        blocks.append(
            f"=== SAMPLE ID: {r['id']} ===\n"
            f"QUESTION: {r['question']}\n\n"
            f"STUDENT ANSWER: {r['student_answer']}\n\n"
            f"DOMAIN CONCEPTS (reference ontology for this sample):\n{r['ontology']}"
        )
    footer = (
        "\n\n" + "=" * 70 + "\nFor EACH sample above, extract concepts and relationships. "
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "results": {\n'
        '    "<SAMPLE ID>": {\n'
        '      "concepts_found": [{"id": "...", "confidence": 0.0-1.0, '
        '"evidence": "...", "is_correct_usage": true}],\n'
        '      "relationships_found": [{"source": "...", "target": "...", '
        '"relation_type": "...", "confidence": 0.0-1.0, "evidence": "...", '
        '"is_correct": true, "misconception_note": ""}],\n'
        '      "unmapped_terms": [],\n'
        '      "overall_depth": "surface|moderate|deep"\n'
        "    }, ...\n"
        "  }\n"
        "}"
    )
    return "\n\n".join(blocks) + footer


def _extract_one_chunk(client, model: str, batch_dir: Path, run_idx: int,
                        chunk_i: int, chunk: list[dict], limiter: "_RateLimiter") -> tuple[int, int, dict]:
    """One (run, chunk) unit of extraction work -- independent of every other
    unit, safe to dispatch concurrently. Returns (run_idx, chunk_i, {sample_id: parsed_result})."""
    batch = [{"id": r["sample_id"], "question": r["question"],
              "student_answer": r["student_answer"], "ontology": r["_ontology"]} for r in chunk]
    prompt = _build_extraction_batch_prompt(batch)
    tag = f"extract_run{run_idx}_c{chunk_i}"
    limiter.acquire()
    result = _call_batched(client, model, EXTRACTION_BATCH_SYSTEM, prompt, batch_dir, tag)
    results = result["parsed"].get("results", result["parsed"])
    expected_ids = {r["sample_id"] for r in chunk}
    if not expected_ids.issubset(results.keys()):
        # Stale cache from a differently-sized run at this same chunk
        # index (e.g. a smaller pilot that didn't fill a full chunk) --
        # the cache key is just the tag, not the sample composition, so
        # this can silently return a subset otherwise. Force one clean
        # refetch rather than proceed with missing samples.
        cache_path = batch_dir / f"{tag}.json"
        print(f"    [cache-mismatch] {tag}: cached result missing "
              f"{len(expected_ids - results.keys())} expected sample(s) "
              f"-- deleting stale cache and refetching")
        cache_path.unlink(missing_ok=True)
        limiter.acquire()
        result = _call_batched(client, model, EXTRACTION_BATCH_SYSTEM, prompt, batch_dir, tag)
        results = result["parsed"].get("results", result["parsed"])
    out = {}
    for r in chunk:
        v = results.get(r["sample_id"])
        if v is None:
            print(f"    [warn] no extraction result for {r['sample_id']} (run {run_idx}, chunk {chunk_i})")
            continue
        out[r["sample_id"]] = v
    print(f"  extraction run {run_idx} chunk {chunk_i}: {len(chunk)} samples done")
    return run_idx, chunk_i, out


def run_all_extraction_batched(rows: list[dict], client, model: str, batch_dir: Path,
                                n_runs: int, workers: int, rpm_cap: int) -> list[dict]:
    """All (run, chunk) units across all n_runs self-consistency passes,
    dispatched concurrently -- they share no state, so nothing about
    correctness depends on run/chunk order. Returns [ {sample_id: parsed}, ... ]
    indexed by run_idx, same shape run_extraction_run_batch used to return
    per call."""
    limiter = _RateLimiter(rpm_cap)
    all_runs: list[dict] = [{} for _ in range(n_runs)]
    tasks = [(run_idx, chunk_i, chunk)
             for run_idx in range(n_runs)
             for chunk_i, chunk in _chunks(rows, CHUNK_SIZE)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_extract_one_chunk, client, model, batch_dir, run_idx, chunk_i, chunk, limiter): (run_idx, chunk_i)
                   for run_idx, chunk_i, chunk in tasks}
        for future in as_completed(futures):
            run_idx, chunk_i, chunk_result = future.result()
            all_runs[run_idx].update(chunk_result)
    return all_runs


def _vote_batch(question: str, answer: str, domain_match_score: float,
                 runs_for_sample: list[dict], domain_graph) -> dict:
    """Offline majority-vote merge across N_RUNS parsed extraction results for
    ONE sample. Mirrors SelfConsistentExtractor._vote() exactly (concept
    voting: mean confidence, majority is_correct_usage, best/highest-
    confidence evidence; relationship voting likewise, restricted to
    accepted concept ids; depth by majority vote), but operating on raw
    parsed dicts (id/confidence/evidence/...) instead of ExtractedConcept
    objects, since these came from batched calls, not per-sample objects.
    Concept/alias validation against the KG (find_concept_by_alias) is
    applied here too, matching ConceptExtractor.extract()'s Step 2/3."""
    concept_votes: dict[str, list] = {}
    for run in runs_for_sample:
        seen_this_run = set()
        for c in run.get("concepts_found", []):
            cid_raw = str(c.get("id", "")).strip()
            if not cid_raw:
                continue
            conf = float(c.get("confidence", 0.5))
            is_correct = bool(c.get("is_correct_usage", True))
            evidence = c.get("evidence", "")
            # Validate/alias-resolve against KG, same as ConceptExtractor.extract()
            if domain_graph.get_concept(cid_raw):
                cid = cid_raw
            else:
                concept = domain_graph.find_concept_by_alias(cid_raw)
                if concept:
                    cid = concept.id
                    conf *= 0.9
                else:
                    continue  # unmapped term, not votable as a concept
            if cid in seen_this_run:
                continue  # avoid double-voting within one run
            seen_this_run.add(cid)
            concept_votes.setdefault(cid, []).append((conf, is_correct, evidence))

    accepted_concepts = []
    for cid, votes in concept_votes.items():
        if len(votes) >= MIN_VOTES:
            mean_conf = round(sum(v[0] for v in votes) / len(votes), 4)
            is_correct = sum(1 for v in votes if v[1]) > len(votes) / 2
            best_evidence = max(votes, key=lambda v: v[0])[2]
            accepted_concepts.append({
                "concept_id": cid, "confidence": mean_conf,
                "evidence": best_evidence, "is_correct_usage": is_correct,
            })
    accepted_ids = {c["concept_id"] for c in accepted_concepts}

    rel_votes: dict[tuple, list] = {}
    for run in runs_for_sample:
        seen_this_run = set()
        for r in run.get("relationships_found", []):
            src, tgt = str(r.get("source", "")).strip(), str(r.get("target", "")).strip()
            if src not in accepted_ids or tgt not in accepted_ids:
                continue
            rtype = r.get("relation_type", "uses")
            key = (src, tgt, rtype)
            if key in seen_this_run:
                continue
            seen_this_run.add(key)
            rel_votes.setdefault(key, []).append((
                float(r.get("confidence", 0.5)), bool(r.get("is_correct", True)),
                r.get("evidence", ""), r.get("misconception_note", ""),
            ))

    accepted_rels = []
    for (src, tgt, rtype), votes in rel_votes.items():
        if len(votes) >= MIN_VOTES:
            mean_conf = round(sum(v[0] for v in votes) / len(votes), 4)
            is_correct = sum(1 for v in votes if v[1]) > len(votes) / 2
            best_evidence = max(votes, key=lambda v: v[0])[2]
            misc_note = next((v[3] for v in votes if v[3]), "")
            accepted_rels.append({
                "source_id": src, "target_id": tgt, "relation_type": rtype,
                "confidence": mean_conf, "evidence": best_evidence,
                "is_correct": is_correct, "misconception_note": misc_note,
            })

    depth_votes = Counter(run.get("overall_depth", "surface") for run in runs_for_sample)
    majority_depth = depth_votes.most_common(1)[0][0] if depth_votes else "surface"

    all_unmapped = list({t for run in runs_for_sample for t in run.get("unmapped_terms", [])})

    return {
        "concepts": accepted_concepts, "relationships": accepted_rels,
        "unmapped_terms": all_unmapped, "overall_depth": majority_depth,
        "domain_match_score": domain_match_score,
        "question": question, "student_answer": answer,
    }


def _filter_by_threshold(concept_graph: dict, threshold: float) -> dict:
    """Mirror the pipeline's post-extraction confidence filter, operating on
    the raw dict shape _vote_batch() returns."""
    filtered_concepts = [c for c in concept_graph["concepts"] if c["confidence"] >= threshold]
    concept_ids = {c["concept_id"] for c in filtered_concepts}
    filtered_rels = [r for r in concept_graph["relationships"]
                      if r["source_id"] in concept_ids and r["target_id"] in concept_ids]
    concept_graph["concepts"] = filtered_concepts
    concept_graph["relationships"] = filtered_rels
    return concept_graph


class _RateLimiter:
    """Thread-safe sliding-window rate limiter: blocks callers so that no
    more than `max_per_minute` acquire() calls succeed in any 60s window.
    Simple deque-of-timestamps implementation -- fine at this call volume
    (hundreds to low thousands of acquisitions, not a hot loop)."""

    def __init__(self, max_per_minute: int):
        import threading
        from collections import deque
        self._max = max_per_minute
        self._lock = threading.Lock()
        self._timestamps = deque()

    def acquire(self):
        while True:
            with self._lock:
                now = time.time()
                while self._timestamps and now - self._timestamps[0] > 60:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return
                wait = 60 - (now - self._timestamps[0]) + 0.05
            time.sleep(max(wait, 0.05))


def _misc_fb_worker(args):
    """Run misconception + false-belief detection for ONE sample. Executed
    concurrently across samples (not batched) -- reuses the real
    MisconceptionDetector/FalseBeliefDetector classes unmodified. Each of
    the up-to-2 LLM calls this makes (misconception is conditional, false-
    belief always fires) acquires a slot from the shared rate limiter
    first, so total throughput stays under the model's rate cap regardless
    of MISC_FB_WORKERS."""
    s, concept_graph, comparison_result, misc_detector, fb_detector, limiter = args
    limiter.acquire()
    misc_report = misc_detector.detect(
        question=s["question"], student_answer=s["student_answer"],
        concept_graph=concept_graph, comparison_result=comparison_result,
    )
    misconceptions = {
        "total_misconceptions": misc_report.total_misconceptions,
        "critical_count": misc_report.critical_count,
        "moderate_count": misc_report.moderate_count,
        "minor_count": misc_report.minor_count,
        "overall_accuracy": misc_report.overall_accuracy,
        "summary": misc_report.summary,
        "misconceptions": [
            {"severity": m.severity.value, "description": m.explanation,
             "student_claim": m.student_claim} for m in misc_report.misconceptions
        ],
    }
    limiter.acquire()
    false_beliefs = fb_detector.detect(question=s["question"], student_answer=s["student_answer"])
    false_beliefs_out = [
        {"severity": fb.severity.value, "student_claim": fb.student_claim,
         "explanation": fb.explanation} for fb in false_beliefs
    ]
    return s["sample_id"], misconceptions, false_beliefs_out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, choices=sorted(MODELS.keys()))
    ap.add_argument("--pilot", type=int, default=0, help="Only process the first N samples (0 = all)")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    tag = args.model
    model_id = MODELS[tag]
    batch_dir = DATA / f"{tag}_pipeline_phaseA_batches"
    out_path = DATA / f"{tag}_pipeline_phaseA_signals.json"

    from datasets.mohler_loader import load_mohler_sample
    dataset = load_mohler_sample()
    samples = dataset.samples[: args.pilot] if args.pilot else dataset.samples
    print(f"Samples: {len(samples)}{' (PILOT)' if args.pilot else ''}")
    print(f"Model: {model_id} (tag={tag})")

    if args.status:
        n_done = 0
        if out_path.exists():
            n_done = len(json.loads(out_path.read_text()))
        print(f"Phase A signals written: {n_done}/{len(samples)}")
        return 0

    from conceptgrade.llm_client import LLMClient, load_openrouter_key
    from graph_comparison.confidence_weighted_comparator import ConfidenceWeightedComparator
    from misconception_detection.detector import MisconceptionDetector, FalseBeliefDetector
    from knowledge_graph.domain_graph import DomainKnowledgeGraph
    from concept_extraction.extractor import (
        ConceptExtractor, StudentConceptGraph, ExtractedConcept, ExtractedRelationship,
    )

    key = load_openrouter_key()
    client = LLMClient(api_key=key)

    with (DATA / "ds_knowledge_graph.json").open() as f:
        kg_data = json.load(f)
    frozen_v1_kg = DomainKnowledgeGraph.from_dict(kg_data)
    assert frozen_v1_kg.num_relationships == 138, (
        f"Expected frozen v1.0-expert KG (138 rel), got {frozen_v1_kg.num_relationships}"
    )
    comparator = ConfidenceWeightedComparator(domain_graph=frozen_v1_kg)
    misc_detector = MisconceptionDetector(api_key=key, model=model_id)
    fb_detector = FalseBeliefDetector(api_key=key, model=model_id)
    # Reuse ConceptExtractor purely for its _build_question_ontology() /
    # find_concept_by_alias() helpers -- no LLM calls made through this instance.
    ontology_helper = ConceptExtractor(domain_graph=frozen_v1_kg, api_key=key, model=model_id)

    rows = []
    for s in samples:
        rows.append({
            "sample_id": s.sample_id, "question_id": s.question_id,
            "question": s.question, "reference_answer": s.reference_answer,
            "student_answer": s.student_answer, "human_score": s.score_avg,
            "_ontology": ontology_helper._build_question_ontology(s.question),
            "_domain_match_score": ontology_helper._last_domain_match_score,
        })

    print(f"\n[1/2] Batched extraction ({N_RUNS} self-consistency runs x "
          f"{len(rows)} samples, chunk size {CHUNK_SIZE}, "
          f"{EXTRACTION_WORKERS} parallel workers)...")
    all_runs = run_all_extraction_batched(rows, client, model_id, batch_dir,
                                           N_RUNS, EXTRACTION_WORKERS, EXTRACTION_RPM_CAP)

    print(f"\n[2/2] Offline majority-vote merge + concurrent misconception/"
          f"false-belief detection ({MISC_FB_WORKERS} workers)...")

    limiter = _RateLimiter(MISC_FB_RPM_CAP)
    merged_rows = []
    misc_fb_args = []
    for r in rows:
        runs_for_sample = [all_runs[i].get(r["sample_id"], {}) for i in range(N_RUNS)]
        merged = _vote_batch(r["question"], r["student_answer"], r["_domain_match_score"],
                              runs_for_sample, frozen_v1_kg)
        merged = _filter_by_threshold(merged, EXTRACTION_CONFIDENCE_THRESHOLD)
        concept_graph_dict = {
            "question": merged["question"], "student_answer": merged["student_answer"],
            "concepts": merged["concepts"], "relationships": merged["relationships"],
            "unmapped_terms": merged["unmapped_terms"], "overall_depth": merged["overall_depth"],
            "domain_match_score": merged["domain_match_score"],
        }

        # Build the real StudentConceptGraph dataclass (not a duck-typed
        # shim) so the comparator sees exactly the object shape it expects,
        # including derived properties like .concept_ids.
        student_graph = StudentConceptGraph(
            question=merged["question"], student_answer=merged["student_answer"],
            concepts=[ExtractedConcept(**c) for c in merged["concepts"]],
            relationships=[ExtractedRelationship(**rel) for rel in merged["relationships"]],
            unmapped_terms=merged["unmapped_terms"], overall_depth=merged["overall_depth"],
            domain_match_score=merged["domain_match_score"],
        )
        comparison = comparator.compare(student_graph=student_graph, question=r["question"]).to_dict()
        merged_rows.append((r, concept_graph_dict, comparison))
        misc_fb_args.append((r, concept_graph_dict, comparison, misc_detector, fb_detector, limiter))

    misc_fb_results = {}
    with ThreadPoolExecutor(max_workers=MISC_FB_WORKERS) as pool:
        futures = {pool.submit(_misc_fb_worker, args): args[0]["sample_id"] for args in misc_fb_args}
        done_count = 0
        for future in as_completed(futures):
            sid = futures[future]
            try:
                sid_r, misconceptions, false_beliefs = future.result()
                misc_fb_results[sid_r] = (misconceptions, false_beliefs)
            except Exception as e:
                print(f"    [warn] misc/fb failed for {sid}: {type(e).__name__}: {e}")
                misc_fb_results[sid] = (
                    {"total_misconceptions": 0, "critical_count": 0, "moderate_count": 0,
                     "minor_count": 0, "overall_accuracy": 1.0, "summary": "ERROR", "misconceptions": []},
                    [],
                )
            done_count += 1
            if done_count % 50 == 0:
                print(f"  misc/fb: {done_count}/{len(misc_fb_args)} done")

    out_rows = []
    for r, concept_graph_dict, comparison in merged_rows:
        misconceptions, false_beliefs = misc_fb_results[r["sample_id"]]
        out_rows.append({
            "sample_id": r["sample_id"], "question_id": r["question_id"],
            "question": r["question"], "reference_answer": r["reference_answer"],
            "student_answer": r["student_answer"], "human_score": r["human_score"],
            "concept_graph": concept_graph_dict, "comparison_result": comparison,
            "misconceptions": misconceptions, "false_beliefs": false_beliefs,
        })

    out_path.write_text(json.dumps(out_rows, indent=2))
    print(f"\nDone: {len(out_rows)}/{len(rows)} in {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
