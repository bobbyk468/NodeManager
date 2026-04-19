"""
run_full_pipeline.py — End-to-end ConceptGrade evaluation pipeline.

Stage 1: Generates KG via Gemini API for DigiKlausur + Kaggle ASAG
Stage 2: Regenerates batch scoring prompts with KG features
Stage 3: Scores all batches via Gemini API
Stage 4: Computes metrics and updates paper report

All intermediate results are saved as JSON for reproducibility.

Usage:
    python3 run_full_pipeline.py                                 # full run (Stages 1–4)
    python3 run_full_pipeline.py --dataset digiklausur           # one dataset
    python3 run_full_pipeline.py --skip-kg                       # skip Stage 1
    python3 run_full_pipeline.py --skip-kg --skip-scoring        # Stages 2+4 only
    python3 run_full_pipeline.py --metrics-only                  # Stage 4 only (ZERO API calls)
    python3 run_full_pipeline.py --only-system c5fix --skip-kg   # re-score C5_fix only

Flag summary:
    --skip-kg       Skip Stage 1 (KG generation). Use cached KG files.
    --skip-scoring  Skip Stage 3 (API scoring). Recompute metrics from existing
                    cached responses in data/batch_responses/ or /tmp/batch_scoring/.
                    Does NOT require GEMINI_API_KEY.
    --metrics-only  Skip Stages 1–3. Run Stage 4 only (score_batch_results.py).
                    Equivalent to --skip-kg --skip-scoring but also skips Stage 2
                    (batch prompt generation). ZERO API calls. Does NOT require
                    GEMINI_API_KEY.
    --force         Re-do all active stages even if cached files exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import glob
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BATCH_DIR = os.environ.get('CONCEPTGRADE_BATCH_DIR', os.path.join(BASE_DIR, 'data', 'tmp'))
BACKEND_ENV = os.path.join(BASE_DIR, "..", "backend", ".env")

# Override with GEMINI_KG_MODEL / GEMINI_SCORING_MODEL / GEMINI_RATE_SLEEP_SEC if needed.
KG_MODEL = os.environ.get("GEMINI_KG_MODEL", "gemini-2.5-flash")
SCORING_MODEL = os.environ.get("GEMINI_SCORING_MODEL", "gemini-2.5-flash")

# Space batch calls to avoid 429; lower only if your quota allows (e.g. 5–8).
RATE_SLEEP = float(os.environ.get("GEMINI_RATE_SLEEP_SEC", "15"))

# Reuse API responses for identical (model + prompt) — set GEMINI_SCORING_CACHE=0 to disable.
SCORING_CACHE_DIR = os.path.join(DATA_DIR, "gemini_scoring_cache")


def load_api_key() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    with open(os.path.abspath(BACKEND_ENV)) as f:
        for line in f:
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    raise RuntimeError("GEMINI_API_KEY not found")


def call_gemini(client, prompt: str, max_tokens: int = 65536, json_mode: bool = True) -> str:
    """Call Gemini and return raw text. Retries on rate limits."""
    from google.genai import types
    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=max_tokens,
        response_mime_type="application/json" if json_mode else None,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=KG_MODEL, contents=prompt, config=config
            )
            if response.text is None:
                raise ValueError("Gemini returned None text")
            return response.text
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = 65 * (attempt + 1)  # 65s > 60s RPM window
                print(f"    Rate limited. Waiting {wait}s... (attempt {attempt+1}/4)")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("All retries exhausted")


# ─── STAGE 1: KG Generation ──────────────────────────────────────────────────

KG_SYSTEM = """You are an expert educator building a Knowledge Graph for automated answer grading.

For each question + reference answer pair, extract:
1. CONCEPTS: Key domain concepts a student must understand (snake_case IDs, 4-10 per question)
2. RELATIONSHIPS: Typed edges between concepts (3-8 per question)

Allowed relationship types: IS_A, HAS_PART, PREREQUISITE_FOR, IMPLEMENTS, USES, VARIANT_OF, HAS_PROPERTY, CONTRASTS_WITH, PRODUCES, OPERATES_ON

Rules:
- Concept IDs must be snake_case, no spaces
- Concepts must be domain terms, not generic words (NOT: "process", "way", "thing")
- Focus on what the reference answer explicitly covers

Return ONLY a JSON object:
{
  "question_kgs": {
    "<question_index>": {
      "question": "<question text>",
      "concepts": [{"id": "concept_id", "name": "Human Name", "description": "one line"}],
      "relationships": [{"from": "concept_a", "to": "concept_b", "type": "TYPE", "weight": 0.9, "description": "why"}],
      "expected_concepts": ["concept_id_1", "concept_id_2"]
    }
  }
}"""


def build_kg_prompt(questions: list[dict], start_idx: int = 0) -> str:
    parts = [KG_SYSTEM, f"\nGenerate KGs for {len(questions)} questions:\n\n"]
    for qi, q in enumerate(questions):
        abs_idx = start_idx + qi
        parts.append(
            f"--- QUESTION {abs_idx} ---\n"
            f"QUESTION: {q['question']}\n\n"
            f"REFERENCE ANSWER:\n{q['reference_answer']}\n\n"
        )
    parts.append(f"\nReturn JSON with question_kgs for indices {start_idx} to {start_idx + len(questions) - 1}.")
    return "".join(parts)


def generate_kg(client, dataset: str, force: bool = False) -> str:
    """Generate KG for a dataset. Returns path to KG JSON file.
    Cache priority: data/{dataset}_auto_kg.json → /tmp/auto_kg_response_{dataset}.json → API call
    """
    out_path = f"/tmp/auto_kg_response_{dataset}.json"
    persistent_path = os.path.join(DATA_DIR, f"{dataset}_auto_kg.json")

    # Check persistent cache first
    if os.path.exists(persistent_path) and not force:
        with open(persistent_path) as f:
            existing = json.load(f)
        n = len(existing.get("question_kgs", existing))
        # Restore to /tmp for downstream scripts
        with open(out_path, "w") as f:
            json.dump(existing, f)
        print(f"  KG loaded from cache ({n} questions) → {persistent_path}")
        return out_path

    if os.path.exists(out_path) and not force:
        with open(out_path) as f:
            existing = json.load(f)
        n = len(existing.get("question_kgs", existing))
        # Also save to persistent cache
        with open(persistent_path, "w") as f:
            json.dump(existing, f)
        print(f"  KG already in /tmp: {n} questions")
        return out_path

    # Load unique questions from question index
    idx_path = os.path.join(DATA_DIR, f"{dataset}_question_index.json")
    if not os.path.exists(idx_path):
        # Generate it first
        subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "generate_auto_kg_prompt.py"), "--dataset", dataset],
            cwd=BASE_DIR, capture_output=True
        )
    with open(idx_path) as f:
        all_questions = json.load(f)

    print(f"  {dataset}: {len(all_questions)} unique questions")

    # Split into chunks of 30 questions (safe for output token limits)
    CHUNK = 30
    all_kgs: dict = {}

    for i in range(0, len(all_questions), CHUNK):
        chunk = all_questions[i:i + CHUNK]
        chunk_end = min(i + CHUNK - 1, len(all_questions) - 1)
        print(f"    KG chunk {i//CHUNK + 1}: questions {i}–{chunk_end} ...", end=" ", flush=True)

        prompt = build_kg_prompt(chunk, start_idx=i)

        try:
            raw = call_gemini(client, prompt, max_tokens=32768, json_mode=True)
            from conceptgrade.llm_client import parse_llm_json
            parsed = parse_llm_json(raw)
            chunk_kgs = parsed.get("question_kgs", parsed)
            all_kgs.update(chunk_kgs)
            print(f"OK ({len(chunk_kgs)} KGs)")
        except Exception as e:
            print(f"ERROR: {e}")
            # Save what we have so far
            break

        if i + CHUNK < len(all_questions):
            print(f"      Waiting {RATE_SLEEP}s...")
            time.sleep(RATE_SLEEP)

    # Save merged KG to both /tmp and persistent data/
    merged = {"question_kgs": all_kgs}
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)
    persistent_path = os.path.join(DATA_DIR, f"{dataset}_auto_kg.json")
    with open(persistent_path, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"  KG saved → {out_path} + {persistent_path} ({len(all_kgs)} questions)")
    return out_path


# ─── STAGE 2: Batch Prompt Generation ────────────────────────────────────────

def generate_batch_prompts(dataset: str) -> tuple[list[str], list[str]]:
    """Regenerate split batch prompts (cllm + c5fix). Returns (cllm_files, c5fix_files)."""
    print(f"  Regenerating split batch prompts for {dataset}...")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "generate_batch_scoring_prompts.py"),
         "--dataset", dataset, "--mode", "split"],
        cwd=BASE_DIR, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-500:]}")
    else:
        for line in result.stdout.split("\n"):
            if "Batch" in line or "Total" in line or "WARNING" in line:
                print(f"    {line}")

    cllm_files = sorted(glob.glob(os.path.join(BATCH_DIR, f"{dataset}_cllm_batch_*.txt")))
    c5fix_files = sorted(glob.glob(os.path.join(BATCH_DIR, f"{dataset}_c5fix_batch_*.txt")))
    return cllm_files, c5fix_files


# ─── STAGE 3: Batch Scoring ───────────────────────────────────────────────────

def _scoring_cache_path(prompt_text: str) -> str:
    key = hashlib.sha256(
        (SCORING_MODEL + "\n" + prompt_text).encode("utf-8")
    ).hexdigest()
    os.makedirs(SCORING_CACHE_DIR, exist_ok=True)
    return os.path.join(SCORING_CACHE_DIR, f"{key}.json")


def score_batch(
    client, prompt_text: str, batch_name: str, *, bypass_cache_read: bool = False
) -> dict:
    """Score one batch. Caches read/write by model+prompt unless GEMINI_SCORING_CACHE=0.
    bypass_cache_read=True skips only the read (e.g. --force still writes cache)."""
    use_cache = os.environ.get("GEMINI_SCORING_CACHE", "1").strip() not in (
        "0",
        "false",
        "no",
    )
    cpath = _scoring_cache_path(prompt_text)
    if use_cache and not bypass_cache_read and os.path.isfile(cpath):
        with open(cpath) as f:
            wrapped = json.load(f)
        return wrapped["result"]

    from google.genai import types
    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=8192,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=SCORING_MODEL, contents=prompt_text, config=config
            )
            if response.text is None:
                raise ValueError("Empty response")
            from conceptgrade.llm_client import parse_llm_json
            parsed = parse_llm_json(response.text)
            if use_cache:
                with open(cpath, "w") as f:
                    json.dump(
                        {
                            "batch_name": batch_name,
                            "model": SCORING_MODEL,
                            "result": parsed,
                        },
                        f,
                        indent=2,
                    )
            return parsed
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = 65 * (attempt + 1)  # 65s > 60s RPM window
                print(f"\n    Rate limited. Waiting {wait}s... (retry {attempt+1}/4)")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("All retries exhausted")


def run_batch_scoring(
    client,
    dataset: str,
    force: bool = False,
    only_system: str = "both",
) -> list[str]:
    """Score split batch files. only_system: 'both' | 'cllm' | 'c5fix'. Returns response JSON paths."""
    cllm_files = sorted(glob.glob(os.path.join(BATCH_DIR, f"{dataset}_cllm_batch_*.txt")))
    c5fix_files = sorted(glob.glob(os.path.join(BATCH_DIR, f"{dataset}_c5fix_batch_*.txt")))
    all_files = [(f, "cllm") for f in cllm_files] + [(f, "c5fix") for f in c5fix_files]
    if only_system == "cllm":
        all_files = [x for x in all_files if x[1] == "cllm"]
    elif only_system == "c5fix":
        all_files = [x for x in all_files if x[1] == "c5fix"]

    if not all_files:
        print(f"  No split batch files found.")
        return []

    print(f"  Scoring {len(cllm_files)} C_LLM + {len(c5fix_files)} C5_fix batches for {dataset}...")
    saved = []
    total = len(all_files)

    for i, (batch_file, system) in enumerate(all_files, 1):
        batch_name = os.path.basename(batch_file).replace(".txt", "")
        resp_path = os.path.join(BATCH_DIR, f"{batch_name}_response.json")

        # Check /tmp first, then persistent backup
        backup_dir = os.path.join(BASE_DIR, "data", "batch_responses")
        backup_path = os.path.join(backup_dir, os.path.basename(resp_path))
        if not os.path.exists(resp_path) and os.path.exists(backup_path) and not force:
            # Restore from persistent cache
            with open(backup_path) as f:
                cached = json.load(f)
            with open(resp_path, "w") as f:
                json.dump(cached, f, indent=2)

        if os.path.exists(resp_path) and not force:
            with open(resp_path) as f:
                existing = json.load(f)
            n = len(existing.get("scores", {}))
            print(f"  [{i}/{total}] {batch_name}: loaded from cache ({n} samples)")
            saved.append(resp_path)
            continue

        print(f"  [{i}/{total}] {batch_name}: scoring...", end=" ", flush=True)
        with open(batch_file) as f:
            prompt_text = f.read()

        try:
            result = score_batch(
                client, prompt_text, batch_name, bypass_cache_read=force
            )
            scores = result.get("scores", {})
            n = len(scores)
            print(f"OK ({n} scores)")

            # Save response JSON to /tmp (working) and data/batch_responses (persistent)
            with open(resp_path, "w") as f:
                json.dump(result, f, indent=2)
            backup_dir = os.path.join(BASE_DIR, "data", "batch_responses")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, os.path.basename(resp_path))
            with open(backup_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"             → Saved {resp_path} + backup")
            saved.append(resp_path)

        except Exception as e:
            print(f"\n  ERROR on {batch_name}: {e}")
            if "quota" in str(e).lower():
                print("  Daily quota exhausted. Stopping.")
                break

        if i < total:
            time.sleep(RATE_SLEEP)

    return saved


# ─── STAGE 4: Compute Metrics ────────────────────────────────────────────────

def compute_metrics(dataset: str) -> bool:
    """Run score_batch_results.py for the dataset. Returns True if successful."""
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "score_batch_results.py"), "--dataset", dataset],
        cwd=BASE_DIR
    )
    return result.returncode == 0


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument("--dataset", choices=["digiklausur", "kaggle_asag", "all"], default="all")
    parser.add_argument("--skip-kg", action="store_true",
                        help="Skip Stage 1: KG generation (use existing cached KG files)")
    parser.add_argument("--skip-scoring", action="store_true",
                        help="Skip Stage 3: API scoring; recompute metrics from cached responses. "
                             "Does NOT require GEMINI_API_KEY.")
    parser.add_argument("--metrics-only", action="store_true",
                        help="Run Stage 4 only: compute metrics from existing cached responses. "
                             "Skips Stages 1–3 entirely. ZERO API calls. "
                             "Does NOT require GEMINI_API_KEY.")
    parser.add_argument("--force", action="store_true",
                        help="Re-do all active stages even if cached files exist")
    parser.add_argument(
        "--only-system",
        choices=["both", "cllm", "c5fix"],
        default="both",
        help="Score only C_LLM batches, only C5_fix batches, or both (saves API when refreshing C5 only).",
    )
    args = parser.parse_args()

    # --metrics-only implies --skip-kg and --skip-scoring
    if args.metrics_only:
        args.skip_kg = True
        args.skip_scoring = True

    datasets = ["digiklausur", "kaggle_asag"] if args.dataset == "all" else [args.dataset]

    # Only load API key when we will actually make API calls (Stage 1 or Stage 3)
    need_api = not args.skip_kg or not args.skip_scoring
    client = None
    if need_api:
        print("Loading Gemini API key...")
        api_key = load_api_key()
        print(f"  Key loaded ({len(api_key)} chars, not shown)")
        from google import genai
        client = genai.Client(api_key=api_key)
    else:
        print("No API calls needed for this run (--skip-kg + --skip-scoring / --metrics-only).")

    os.makedirs(BATCH_DIR, exist_ok=True)

    for dataset in datasets:
        print(f"\n{'='*65}")
        print(f"  PIPELINE: {dataset}")
        print(f"{'='*65}")

        # Stage 1: KG Generation
        if not args.skip_kg:
            print(f"\n[Stage 1] Generating KG for {dataset}...")
            try:
                kg_path = generate_kg(client, dataset, force=args.force)
                print(f"  KG ready: {kg_path}")
                time.sleep(RATE_SLEEP)
            except Exception as e:
                print(f"  KG generation failed: {e}")
                print("  Continuing with empty KG features...")
        else:
            print(f"\n[Stage 1] Skipped (--skip-kg)")

        # Stage 2: Batch prompts (skip when --metrics-only; still run for --skip-scoring alone)
        if not args.metrics_only:
            print(f"\n[Stage 2] Building split batch prompts for {dataset}...")
            cllm_files, c5fix_files = generate_batch_prompts(dataset)
            print(f"  {len(cllm_files)} C_LLM + {len(c5fix_files)} C5_fix batch files ready")
        else:
            print(f"\n[Stage 2] Skipped (--metrics-only)")
            cllm_files = sorted(glob.glob(os.path.join(BATCH_DIR, f"{dataset}_cllm_batch_*.txt")))
            c5fix_files = sorted(glob.glob(os.path.join(BATCH_DIR, f"{dataset}_c5fix_batch_*.txt")))

        n_total = len(cllm_files) + len(c5fix_files)
        if args.only_system == "cllm":
            n_total = len(cllm_files)
        elif args.only_system == "c5fix":
            n_total = len(c5fix_files)

        # Stage 3: Scoring
        saved: list[str] = []
        if not args.skip_scoring:
            print(f"\n[Stage 3] Scoring batches for {dataset} (--only-system {args.only_system})...")
            saved = run_batch_scoring(
                client, dataset, force=args.force, only_system=args.only_system
            )
            print(f"  {len(saved)}/{n_total} batches scored this run")
        else:
            print(f"\n[Stage 3] Skipped (--skip-scoring / --metrics-only)")

        # Stage 4: Metrics — always runs (reads from cached responses)
        print(f"\n[Stage 4] Computing metrics for {dataset}...")
        ok = compute_metrics(dataset)
        if not ok:
            print(f"  Metrics computation failed for {dataset}")

        # Stage 4b: Dashboard extras (radar + heatmap) — no API, always run
        print(f"\n[Stage 4b] Generating dashboard extras for {dataset}...")
        subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "generate_dashboard_extras.py"),
             "--dataset", dataset],
            cwd=BASE_DIR,
        )

    # Regenerate paper report
    print(f"\n{'='*65}")
    print("  Regenerating paper report v2...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "generate_paper_report_v2.py")], cwd=BASE_DIR)

    # Export CSVs
    print(f"\n{'='*65}")
    print("  Exporting results to CSV...")
    subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "export_results_csv.py"),
         "--dataset", args.dataset],
        cwd=BASE_DIR,
    )

    print("\n✓ Pipeline complete.")


if __name__ == "__main__":
    main()
