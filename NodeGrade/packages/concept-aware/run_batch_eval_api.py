"""
run_batch_eval_api.py — Automated batch scoring via Gemini API.

Reads pre-generated batch prompt files from /tmp/batch_scoring/,
sends each to Gemini, saves the JSON response, then calls score_batch_results.py.

Usage:
    python3 run_batch_eval_api.py --dataset digiklausur
    python3 run_batch_eval_api.py --dataset kaggle_asag
    python3 run_batch_eval_api.py --dataset all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_DIR = os.environ.get('CONCEPTGRADE_BATCH_DIR', os.path.join(BASE_DIR, 'data', 'tmp'))
BACKEND_ENV = os.path.join(BASE_DIR, "..", "backend", ".env")
MODEL = "gemini-2.5-flash"

# Free tier: 10 RPM → wait 7 sec between calls to stay safe
RATE_LIMIT_SLEEP = 7


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
    raise RuntimeError("GEMINI_API_KEY not found in .env")


def call_gemini_batch(client, prompt_text: str, batch_id: str) -> dict:
    """Send one batch prompt to Gemini, return parsed JSON scores dict."""
    from google.genai import types

    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=8192,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt_text,
        config=config,
    )

    raw = response.text
    if not raw:
        raise ValueError(f"Empty response for batch {batch_id}")

    # Parse JSON
    from conceptgrade.llm_client import parse_llm_json
    parsed = parse_llm_json(raw)
    return parsed


def process_dataset(dataset: str, api_key: str, force: bool = False) -> list[str]:
    """Process all batch files for a dataset. Returns list of saved response paths."""
    from google import genai

    client = genai.Client(api_key=api_key)

    # Find all batch prompt files
    pattern = os.path.join(BATCH_DIR, f"{dataset}_batch_*.txt")
    batch_files = sorted(glob.glob(pattern))

    if not batch_files:
        print(f"  No batch files found: {pattern}")
        return []

    print(f"\n{'='*65}")
    print(f"  Dataset: {dataset}  ({len(batch_files)} batches, model={MODEL})")
    print(f"{'='*65}")

    saved_paths = []
    total_scored = 0

    for i, batch_file in enumerate(batch_files, 1):
        batch_name = os.path.basename(batch_file).replace(".txt", "")
        resp_path = os.path.join(BATCH_DIR, f"{batch_name}_response.json")

        if os.path.exists(resp_path) and not force:
            print(f"  [{i}/{len(batch_files)}] {batch_name}: already done → {resp_path}")
            # Count existing scored items
            with open(resp_path) as f:
                existing = json.load(f)
            total_scored += len(existing.get("scores", {}))
            saved_paths.append(resp_path)
            continue

        print(f"  [{i}/{len(batch_files)}] {batch_name}: sending to Gemini...", end=" ", flush=True)

        with open(batch_file) as f:
            prompt_text = f.read()

        retries = 0
        while retries < 3:
            try:
                result = call_gemini_batch(client, prompt_text, batch_name)
                scores = result.get("scores", {})
                n = len(scores)
                print(f"OK ({n} scores)")

                # Save response
                with open(resp_path, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"             Saved → {resp_path}")

                saved_paths.append(resp_path)
                total_scored += n
                break

            except Exception as e:
                retries += 1
                err_msg = str(e)[:100]
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    wait = 30 * retries
                    print(f"\n    Rate limited. Waiting {wait}s... (retry {retries}/3)")
                    time.sleep(wait)
                elif "quota" in err_msg.lower():
                    print(f"\n    QUOTA EXHAUSTED at batch {i}/{len(batch_files)}: {err_msg}")
                    sentinel = os.path.join(BATCH_DIR, f"{dataset}_INCOMPLETE_{i}of{len(batch_files)}.flag")
                    with open(sentinel, 'w') as sf:
                        sf.write(json.dumps({
                            'exhausted_at_batch': i,
                            'total_batches': len(batch_files),
                            'saved_paths': saved_paths,
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        }))
                    print(f"    Sentinel written: {sentinel}")
                    print("    Re-run after quota resets. Remaining batches will resume automatically.")
                    return saved_paths
                else:
                    print(f"\n    ERROR (retry {retries}/3): {err_msg}")
                    time.sleep(10)

        if i < len(batch_files):
            print(f"             Waiting {RATE_LIMIT_SLEEP}s (rate limit)...")
            time.sleep(RATE_LIMIT_SLEEP)

    print(f"\n  Done: {total_scored} samples scored across {len(saved_paths)} batches")
    return saved_paths


def run_scoring(dataset: str) -> None:
    """Run score_batch_results.py for the dataset."""
    import subprocess
    print(f"\n  Running score_batch_results.py --dataset {dataset} ...")
    script = os.path.join(BASE_DIR, "score_batch_results.py")
    result = subprocess.run(
        [sys.executable, script, "--dataset", dataset],
        capture_output=False,
        cwd=BASE_DIR,
    )
    if result.returncode != 0:
        print(f"  WARNING: score_batch_results.py exited with code {result.returncode}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["digiklausur", "kaggle_asag", "all"], default="all")
    parser.add_argument("--force", action="store_true", help="Re-score even if response already exists")
    args = parser.parse_args()

    print(f"Loading Gemini API key...")
    api_key = load_api_key()
    print(f"  Key loaded (prefix: {api_key[:12]}...)")

    datasets = ["digiklausur", "kaggle_asag"] if args.dataset == "all" else [args.dataset]

    for dataset in datasets:
        saved = process_dataset(dataset, api_key, force=args.force)
        if saved:
            run_scoring(dataset)

    # Regenerate paper report if both datasets done
    digi_done = os.path.exists(os.path.join(BASE_DIR, "data", "digiklausur_eval_results.json"))
    kaggle_done = os.path.exists(os.path.join(BASE_DIR, "data", "kaggle_asag_eval_results.json"))

    if digi_done or kaggle_done:
        print(f"\n{'='*65}")
        print("  Regenerating paper report v2...")
        import subprocess
        script = os.path.join(BASE_DIR, "generate_paper_report_v2.py")
        subprocess.run([sys.executable, script], cwd=BASE_DIR)

    print("\nAll done.")


if __name__ == "__main__":
    main()
