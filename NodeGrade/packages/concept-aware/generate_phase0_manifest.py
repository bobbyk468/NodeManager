#!/usr/bin/env python3
"""
generate_phase0_manifest.py -- generates docs/PHASE0_RUN_MANIFEST_2026-08-19.json
without a self-reference cycle (2026-08-19, fifth review round).

The problem this replaces: earlier versions of the manifest recorded a
config's own "pinned_commit", which was always at least one commit stale
by construction -- a commit cannot contain its own not-yet-computed
hash, so every attempt to "fix" the pin by re-pinning to a newer commit
was itself a new commit needing a new pin. Commit 7dc6085's re-pin also
silently changed config_fingerprint()'s output (see REPRODUCIBILITY.md
Finding 6), compounding the problem.

The fix, used by this script:
  1. This script is run ONLY against an already-committed, clean working
     tree (HEAD == the "code commit" -- the last substantive code change,
     with no manifest file in it yet). It reads the CURRENT HEAD's commit
     SHA and tree hash directly from git -- never a value baked into a
     config or hardcoded here.
  2. The resulting manifest is committed SEPARATELY, as the very next
     commit, containing ONLY the manifest file (a metadata-only commit).
     That new commit's parent is, by construction, exactly the commit
     this script read HEAD as -- no cycle, because the manifest commit
     never needs to reference its own hash, only its parent's.
  3. verify_investigation_integrity.py's check_manifest_provenance()
     independently re-derives "the commit that introduced/last touched
     the manifest file" from git history and its parent's tree hash, and
     fails unless both match what's recorded here -- so this script's
     output can't drift from reality undetected.

Refuses to run (prints an error, exits 1) if:
  - the working tree is dirty (the "code commit" must be a real,
    complete commit, not a mix of committed + uncommitted state), or
  - the manifest file itself has uncommitted or already-committed
    changes pending in the index (this script's OWN job is to produce
    that file for a fresh, separate commit -- if it's already tracked
    and unchanged, that means a manifest for the current HEAD already
    exists and doesn't need regenerating).

Run:
    python3 generate_phase0_manifest.py
    git add docs/PHASE0_RUN_MANIFEST_2026-08-19.json
    git commit -m "..."
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"
MANIFEST_PATH = BASE / "docs" / "PHASE0_RUN_MANIFEST_2026-08-19.json"

# The 18 restricted paths -- must stay in sync with .gitignore's
# "Restricted artifacts" section. Listed explicitly (not globbed) for
# the same auditability reason .gitignore uses explicit paths.
RESTRICTED_ARTIFACTS = [
    ("data/claude_pipeline_phaseA_batches", "raw_batch_cache"),
    ("data/claude_pipeline_phaseA_signals.json", "student_answer_text"),
    ("data/deepseek_pipeline_phaseA_batches", "raw_batch_cache"),
    ("data/deepseek_pipeline_phaseA_signals.json", "student_answer_text"),
    ("data/deepseek_pipeline_phaseB_batches", "raw_batch_cache"),
    ("data/deepseek_pipeline_phaseB_batches_pilot20", "raw_batch_cache"),
    ("data/deepseek_verifier_ablation_batches", "raw_batch_cache"),
    ("data/deepseek_verifier_skeptical_batches", "raw_batch_cache"),
    ("data/gpt_pipeline_phaseA_batches", "raw_batch_cache"),
    ("data/gpt_pipeline_phaseA_signals.json", "student_answer_text"),
    ("data/gpt_pipeline_phaseB_batches", "raw_batch_cache"),
    ("data/gpt_pipeline_phaseB_batches_pilot20", "raw_batch_cache"),
    ("data/gpt_verifier_ablation_batches", "raw_batch_cache"),
    ("data/gpt_verifier_skeptical_batches", "raw_batch_cache"),
    ("data/mohler_real_verifier_corrected_cov_batches", "raw_batch_cache"),
    ("data/mohler_real_verifier_evidence_removed_batches", "raw_batch_cache"),
    ("data/mohler_real_verifier_skeptical_batches", "raw_batch_cache"),
    ("data/mohler_real_verifier_targeted_batches", "raw_batch_cache"),
]

TEST_COMMANDS = [
    "python3 verify_all_paper_claims.py",
    "python3 test_pipeline_integrity.py",
    "python3 test_relationship_direction.py",
    "python3 verify_investigation_integrity.py",
]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=BASE, capture_output=True, text=True, check=True,
    ).stdout.strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fingerprint_artifact(rel_path: str) -> dict:
    """Content fingerprint for one restricted path, file or directory.
    A directory's fingerprint is the sha256 of its sorted
    "relative_file_path:sha256\\n" listing -- a verifiable composite
    hash without needing to store one hash per file in the manifest."""
    path = BASE / rel_path
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        return {"exists": True, "type": "file", "sha256": _sha256_file(path)}
    files = sorted(p for p in path.rglob("*") if p.is_file())
    lines = [f"{p.relative_to(path).as_posix()}:{_sha256_file(p)}" for p in files]
    composite = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    total_size = sum(p.stat().st_size for p in files)
    return {
        "exists": True, "type": "directory", "file_count": len(files),
        "total_bytes": total_size, "composite_sha256": composite,
    }


def main() -> int:
    porcelain = _git("status", "--porcelain")
    if porcelain:
        # A restricted path being untracked-but-gitignored is fine and
        # expected -- .gitignore entries don't show up in --porcelain at
        # all once ignored, so any output here is a REAL dirty-tree
        # condition (staged or unstaged changes to tracked files, or
        # untracked non-ignored files) that must be resolved first.
        print("ERROR: working tree is not clean -- refusing to generate a "
              "manifest against a mix of committed and uncommitted state.")
        print(porcelain)
        return 1

    code_commit = _git("rev-parse", "HEAD")
    code_commit_short = _git("rev-parse", "--short", "HEAD")
    code_commit_tree = _git("rev-parse", "HEAD^{tree}")

    from conceptgrade.configs import REGISTRY, config_identity

    restricted = {}
    for rel_path, reason in RESTRICTED_ARTIFACTS:
        restricted[rel_path] = {"reason": reason, **_fingerprint_artifact(rel_path)}

    manifest = {
        "phase": "Phase 0 integrity work",
        "generated": "2026-08-19 (fifth review round -- self-reference-free provenance)",
        "code_commit": code_commit,
        "code_commit_short": code_commit_short,
        "code_commit_tree_hash": code_commit_tree,
        "note": (
            "code_commit/code_commit_tree_hash identify the commit this "
            "manifest describes -- read directly from `git rev-parse HEAD` "
            "at generation time, against a verified-clean working tree. "
            "This manifest file is committed SEPARATELY, as the immediate "
            "next commit after code_commit, containing only this file. "
            "verify_investigation_integrity.py's check_manifest_provenance() "
            "independently re-derives the manifest commit's actual parent "
            "and tree hash from git history and fails unless both match "
            "what's recorded here -- see conceptgrade/configs.py's module "
            "docstring 'Commit provenance' section for why a per-config "
            "pinned_commit field (the prior approach) could never work."
        ),
        "configs": {name: config_identity(cfg) for name, cfg in REGISTRY.items()},
        "test_commands": TEST_COMMANDS,
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "packages": {
                pkg: __import__(pkg).__version__
                for pkg in ("numpy", "scipy", "sklearn")
            },
        },
        "restricted_artifacts": restricted,
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[generated] {MANIFEST_PATH}")
    print(f"  code_commit={code_commit_short} tree={code_commit_tree[:12]}")
    print(f"  {len(restricted)} restricted artifacts fingerprinted")
    print("\nNext: git add docs/PHASE0_RUN_MANIFEST_2026-08-19.json && git commit "
          "(as a SEPARATE, metadata-only commit -- do not add other files to it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
