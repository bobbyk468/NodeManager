#!/usr/bin/env python3
"""
Verify services required for ConceptGrade dashboard testing are reachable.

Use before manual QA or before npm run verify:visualization.

Examples:
  python3 scripts/dashboard_test_prerequisites.py
  python3 scripts/dashboard_test_prerequisites.py --frontend http://localhost:5173
  python3 scripts/dashboard_test_prerequisites.py --wait 90 --frontend http://localhost:5173
  python3 scripts/dashboard_test_prerequisites.py --run-verify   # then runs API smoke test

Exit 0: all required (and requested) checks passed.
Exit 1: failure or timeout — stderr explains what to start.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def check_api(base: str, timeout: float) -> tuple[bool, str]:
    url = f"{base.rstrip('/')}/api/visualization/datasets"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False, f"{url} returned HTTP {resp.status}"
            return True, url
    except urllib.error.HTTPError as e:
        return False, f"{url} -> HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"{url} -> {e.reason!s}"
    except Exception as e:
        return False, f"{url} -> {e!s}"


def check_frontend(url: str, timeout: float) -> tuple[bool, str]:
    root = url.rstrip("/") + "/"
    try:
        req = urllib.request.Request(
            root,
            headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False, f"{root} returned HTTP {resp.status}"
            return True, root
    except urllib.error.HTTPError as e:
        return False, f"{root} -> HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"{root} -> {e.reason!s}"
    except Exception as e:
        return False, f"{root} -> {e!s}"


def wait_until(
    label: str,
    fn,
    wait_seconds: float,
    interval: float,
) -> tuple[bool, str]:
    if wait_seconds <= 0:
        ok, msg = fn()
        return ok, msg

    deadline = time.monotonic() + wait_seconds
    last_msg = ""
    while time.monotonic() < deadline:
        ok, msg = fn()
        last_msg = msg
        if ok:
            return True, msg
        time.sleep(interval)
    return False, f"{label}: still not ready after {wait_seconds:.0f}s (last: {last_msg})"


def print_start_hints(api_ok: bool, fe_ok: bool | None, frontend_requested: bool) -> None:
    print("\n--- Start commands (from repo root NodeGrade/) ---", file=sys.stderr)
    if not api_ok:
        print(
            "  Backend (required for API + dashboard data):",
            file=sys.stderr,
        )
        print("    cd packages/backend && npm run start:dev", file=sys.stderr)
        print("    # default port 5000 — set PORT=... if you use another", file=sys.stderr)
    if frontend_requested and fe_ok is False:
        print("  Frontend (required for browser / TC-UI-*):", file=sys.stderr)
        print("    cd packages/frontend && npx vite --host 0.0.0.0", file=sys.stderr)
        print("    # default http://localhost:5173", file=sys.stderr)
    print(
        "  Align API URL: packages/frontend/public/config/env.development.json → API",
        file=sys.stderr,
    )
    print("---", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--api-base",
        default="http://localhost:5000",
        help="NestJS origin (no trailing slash)",
    )
    ap.add_argument(
        "--frontend",
        default="",
        help="If set (e.g. http://localhost:5173), require Vite dev server reachable at /",
    )
    ap.add_argument(
        "--wait",
        type=float,
        default=0.0,
        help="Seconds to poll API (and frontend if set) until up (0 = single attempt)",
    )
    ap.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between polls when --wait > 0",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request timeout (seconds)",
    )
    ap.add_argument(
        "--run-verify",
        action="store_true",
        help="After checks pass, run scripts/verify_visualization_api.py with same --api-base",
    )
    args = ap.parse_args()
    base = args.api_base.rstrip("/")
    timeout = args.timeout
    fe_url = (args.frontend or "").strip()

    def api_check() -> tuple[bool, str]:
        return check_api(base, timeout)

    api_ok, api_msg = wait_until(
        "NestJS visualization API",
        api_check,
        args.wait,
        args.interval,
    )
    if api_ok:
        print(f"OK: visualization API reachable ({api_msg})")
    else:
        print(f"FAIL: {api_msg}", file=sys.stderr)
        print_start_hints(False, None, bool(fe_url))
        return 1

    fe_ok: bool | None = None
    if fe_url:
        def fe_check() -> tuple[bool, str]:
            return check_frontend(fe_url, timeout)

        fe_ok, fe_msg = wait_until(
            "Frontend dev server",
            fe_check,
            args.wait,
            args.interval,
        )
        if fe_ok:
            print(f"OK: frontend reachable ({fe_msg})")
        else:
            print(f"FAIL: {fe_msg}", file=sys.stderr)
            print_start_hints(True, False, True)
            return 1

    if args.run_verify:
        script_dir = Path(__file__).resolve().parent
        verify = script_dir / "verify_visualization_api.py"
        cmd = [sys.executable, str(verify), "--base", base, "--timeout", str(timeout)]
        print("Running API smoke test:", " ".join(cmd))
        r = subprocess.run(cmd, cwd=script_dir.parent)
        if r.returncode != 0:
            return r.returncode

    print("Prerequisites satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
