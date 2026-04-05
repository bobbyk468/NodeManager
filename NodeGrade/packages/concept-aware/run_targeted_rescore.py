"""
Automatically call Gemini to re-score the 8 targeted samples.

Reads the prompt from /tmp/rescore_targeted_7.txt,
calls gemini-2.0-flash-latest, and saves response to
/tmp/rescore_targeted_response.json.

Then runs score_targeted_rescore.py to show the updated per-question analysis.

Usage:
    python3 run_targeted_rescore.py
"""
from __future__ import annotations

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

PROMPT_PATH = "/tmp/rescore_targeted_7.txt"
RESPONSE_PATH = "/tmp/rescore_targeted_response.json"
MODEL = "gemini-2.0-flash"

# Load API key from backend .env
BACKEND_ENV = os.path.join(
    BASE_DIR, "..", "backend", ".env"
)

SEP = "─" * 72


def load_api_key() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    env_path = os.path.abspath(BACKEND_ENV)
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    raise RuntimeError(
        "GEMINI_API_KEY not found in environment or backend/.env"
    )


def main() -> None:
    print(SEP)
    print("Running Targeted Re-score via Gemini API")
    print(SEP)

    api_key = load_api_key()
    print(f"API key loaded (prefix: {api_key[:8]}...)")

    if not os.path.exists(PROMPT_PATH):
        print(f"ERROR: {PROMPT_PATH} not found. Run generate_targeted_rescore.py first.")
        sys.exit(1)

    with open(PROMPT_PATH) as f:
        prompt_text = f.read()
    print(f"Prompt loaded: {len(prompt_text):,} chars")

    from conceptgrade.llm_client import LLMClient, parse_llm_json

    client = LLMClient(api_key=api_key)
    print(f"Calling {MODEL}...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0.1,
        max_tokens=1024,
        json_mode=True,
    )
    raw_text = response.choices[0].message.content
    print(f"Response received ({len(raw_text)} chars)")

    # Parse JSON
    parsed = parse_llm_json(raw_text)
    scores = parsed.get("scores", parsed)

    # Normalise: ensure each value is a float (not dict)
    normalised = {}
    for k, v in scores.items():
        if isinstance(v, dict):
            normalised[k] = float(v.get("holistic_score", v.get("score", 0.0)))
        else:
            normalised[k] = float(v)

    result = {"scores": normalised, "raw": raw_text[:2000]}
    with open(RESPONSE_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Response saved → {RESPONSE_PATH}")

    # Show raw scores
    print(f"\nGemini scores for targeted IDs:")
    for sid in sorted(normalised.keys(), key=int):
        print(f"  ID {sid}: {normalised[sid]}")

    print(SEP)
    print("Running score analysis...")
    print(SEP)

    import importlib.util, subprocess
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "score_targeted_rescore.py")],
        cwd=BASE_DIR,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
