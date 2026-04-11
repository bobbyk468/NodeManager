#!/usr/bin/env python3
"""
Smoke test for ConceptGrade visualization API.

Requires a running NestJS backend. Prefer checking reachability first:

  npm run check:dashboard-test-env
  npm run verify:visualization

Or one command: npm run test:dashboard

Direct: python3 scripts/verify_visualization_api.py --base http://localhost:5000

Checks:
  - GET /api/visualization/datasets returns a non-empty list
  - For each dataset, GET /api/visualization/datasets/:name returns exactly 9
    visualizations with the expected viz_id set
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

EXPECTED_VIZ_IDS = frozenset(
    {
        "class_summary",
        "blooms_dist",
        "solo_dist",
        "score_comparison",
        "concept_frequency",
        "chain_coverage_dist",
        "score_scatter",
        "student_radar",
        "misconception_heatmap",
    }
)


def fetch_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--base",
        default="http://localhost:5000",
        help="API origin without trailing slash (default: http://localhost:5000)",
    )
    ap.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout seconds")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    timeout = args.timeout

    list_url = f"{base}/api/visualization/datasets"
    try:
        data = fetch_json(list_url, timeout)
    except urllib.error.HTTPError as e:
        print(f"FAIL: {list_url} -> HTTP {e.code}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"FAIL: {list_url} -> {e.reason}", file=sys.stderr)
        print("Hint: start the backend (npm run start:dev) and match --base to PORT.", file=sys.stderr)
        return 1

    datasets = data.get("datasets", [])
    if not isinstance(datasets, list) or not datasets:
        print("FAIL: expected non-empty datasets array", file=sys.stderr)
        return 1

    print(f"OK: GET /api/visualization/datasets -> {datasets}")

    for name in datasets:
        url = f"{base}/api/visualization/datasets/{name}"
        try:
            body = fetch_json(url, timeout)
        except urllib.error.HTTPError as e:
            print(f"FAIL: {url} -> HTTP {e.code}", file=sys.stderr)
            return 1
        except urllib.error.URLError as e:
            print(f"FAIL: {url} -> {e.reason}", file=sys.stderr)
            return 1

        viz = body.get("visualizations", [])
        if not isinstance(viz, list) or len(viz) != 9:
            print(
                f"FAIL: {name} expected 9 visualizations, got {len(viz) if isinstance(viz, list) else type(viz)}",
                file=sys.stderr,
            )
            return 1

        got = frozenset(v.get("viz_id") for v in viz if isinstance(v, dict))
        if got != EXPECTED_VIZ_IDS:
            print(
                f"FAIL: {name} viz_id mismatch\n"
                f"  expected: {sorted(EXPECTED_VIZ_IDS)}\n"
                f"  got:      {sorted(got)}",
                file=sys.stderr,
            )
            return 1

        print(f"OK: {name} -> 9 specs, viz_ids match")

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
