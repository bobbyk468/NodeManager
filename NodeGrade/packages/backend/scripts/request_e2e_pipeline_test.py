#!/usr/bin/env python3
"""
End-to-end pipeline test request — runs automated gates, then prints copy-paste
instructions for local QA and (optional) remote browser handoff.

Usage (from packages/backend, with Nest + eval data ready):
  python3 scripts/request_e2e_pipeline_test.py
  python3 scripts/request_e2e_pipeline_test.py --frontend http://localhost:5173
  python3 scripts/request_e2e_pipeline_test.py --api-base http://localhost:5000 --wait 60

npm:  npm run request:e2e-test
       npm run request:e2e-test -- --frontend http://localhost:5173

Exits 1 if prerequisite or visualization verify fails (no handoff printed).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_NODEGRADE = BACKEND_DIR.parent.parent  # packages/backend -> NodeGrade root (monorepo task-evaluation root)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--api-base",
        default="http://localhost:5001",
        help="Nest origin (match Nest log / env.development.json API)",
    )
    ap.add_argument(
        "--frontend",
        default="",
        help="If set, prerequisite also checks Vite (e.g. http://localhost:5173)",
    )
    ap.add_argument("--wait", type=float, default=0.0, help="Seconds to wait for services (prerequisite script)")
    ap.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout for checks")
    args = ap.parse_args()

    pre = [sys.executable, str(SCRIPT_DIR / "dashboard_test_prerequisites.py"), "--api-base", args.api_base]
    if args.frontend:
        pre.extend(["--frontend", args.frontend])
    if args.wait > 0:
        pre.extend(["--wait", str(args.wait)])
    pre.extend(["--timeout", str(args.timeout)])

    print("== Step 1/2: Prerequisites ==")
    r1 = subprocess.run(pre, cwd=BACKEND_DIR)
    if r1.returncode != 0:
        print("\nAbort: fix services (see stderr above), then re-run this script.", file=sys.stderr)
        return 1

    verify = [
        sys.executable,
        str(SCRIPT_DIR / "verify_visualization_api.py"),
        "--base",
        args.api_base.rstrip("/"),
        "--timeout",
        str(args.timeout),
    ]
    print("\n== Step 2/2: Visualization API smoke (9 specs per dataset) ==")
    r2 = subprocess.run(verify, cwd=BACKEND_DIR)
    if r2.returncode != 0:
        print("\nAbort: API contract failed — check DATA_DIR / eval JSON.", file=sys.stderr)
        return 1

    doc_remote = REPO_NODEGRADE / "packages/concept-aware/docs/ConceptGrade_Dashboard_E2E_Remote_Browser.md"
    doc_local = REPO_NODEGRADE / "packages/concept-aware/docs/ConceptGrade_Dashboard_Manual_Test_Guide.md"

    print("\n")
    print("=" * 72)
    print("AUTOMATED GATES PASSED — E2E test request (copy sections below as needed)")
    print("=" * 72)

    print(
        """
--- A) Local browser / human QA (same machine as Nest + Vite) ---

1. Open the manual test guide and run TC-PRE-001 through TC-ACC-001:
"""
    )
    print(f"   file://{doc_local}")
    print(f"   API verified at: {args.api_base}")
    print("   Typical UI: http://localhost:5173/dashboard (match Vite port if different).")

    print(
        """
--- B) Remote AI browser (Comet, etc.) — requires HTTPS tunnels ---

Paste this block FIRST (fill both URLs), then paste the full remote E2E doc:

FRONTEND_BASE=https://YOUR-FRONTEND-TUNNEL.example.ngrok-free.app
API_BASE=https://YOUR-API-TUNNEL.example.ngrok-free.app

Then paste the contents of:
"""
    )
    print(f"   file://{doc_remote}")

    print(
        """
Tunnel the same ports Nest/Vite use; add CORS for FRONTEND_BASE; set SPA API to API_BASE/
(see section 2 of that doc).

--- C) Optional: full stack reminder ---

- Backend:  cd packages/backend && npm run start:dev
- Frontend: cd packages/frontend && npx vite --host 0.0.0.0
- Postgres: must be up for Nest (DATABASE_URL in packages/backend/.env)
"""
    )
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
