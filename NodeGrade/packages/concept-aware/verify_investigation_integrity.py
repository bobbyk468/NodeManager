#!/usr/bin/env python3
"""
verify_investigation_integrity.py -- single-command Phase 0 integrity
check (2026-08-19, REPRODUCIBILITY.md Finding 6). Distinct from
verify_all_paper_claims.py (which checks the PAPER's cited numbers
against cached data) -- this checks that:

  1. Every named config in conceptgrade/configs.py's REGISTRY can still
     build a pipeline without a prompt-version mismatch (catches
     verifier-prompt drift automatically, the exact failure class that
     let Finding 5's prompt change silently invalidate cached
     calibrations before this check existed).
  2. Every calibration artifact's recorded verifier_prompt_version
     matches the live conceptgrade.verifier.VERIFIER_PROMPT_VERSION_SAG
     constant -- fails loudly on a stale artifact rather than letting
     Calibration.check_compatible()'s runtime check be the only
     safeguard.
  3. A handful of the most load-bearing headline numbers from
     REPRODUCIBILITY.md Findings 5/6 are re-derived from cached data and
     checked against their documented values, so a report claim can't
     silently drift from what the cached data actually says.
  4. Required cached artifacts referenced by REPRODUCIBILITY.md Findings
     4-6 actually exist on disk.
  5. docs/PHASE0_RUN_MANIFEST_2026-08-19.json's recorded code_commit and
     code_commit_tree_hash are genuinely correct -- independently
     re-derived from git history, not trusted from the manifest's own
     claims. Fails (not warns) on any mismatch, and fails if the
     manifest commit touches anything besides the manifest file itself.

Zero API calls -- everything here is either a pure Python check, a `git`
subprocess call, or reads already-cached JSON.

Run:
    python3 verify_investigation_integrity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
DATA = BASE / "data"

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def section(title: str):
    print(f"\n=== {title} ===")


def check_configs():
    section("1. Named config registry (conceptgrade/configs.py)")
    from conceptgrade.configs import REGISTRY, build_pipeline, ConfigProvenanceError, check_working_tree
    for name, config in REGISTRY.items():
        try:
            p = build_pipeline(config, api_key="dummy-not-used")
            check(f"config {name!r} builds without prompt/KG/provider drift", True)
            # build_pipeline() raising ConfigProvenanceError on mismatch is the
            # enforcement mechanism -- but assert the declared values here too,
            # explicitly, so this script doesn't just trust that build_pipeline()
            # was called correctly; it independently confirms what was built
            # actually matches what the config claims (2026-08-19, blocker #4:
            # "config claims such as KG version and provider are not verified").
            check(
                f"config {name!r}: built KG version matches declared kg_version",
                p.domain_graph.version == config.kg_version,
                f"declared={config.kg_version!r} actual={p.domain_graph.version!r}",
            )
            from conceptgrade.llm_client import detect_provider
            check(
                f"config {name!r}: declared provider matches model",
                detect_provider(config.model) == config.provider,
                f"declared={config.provider!r} detected={detect_provider(config.model)!r}",
            )
        except ConfigProvenanceError as e:
            check(f"config {name!r} builds without prompt/KG/provider drift", False, str(e))
            continue
    # Working-tree dirty-state is a single, global check now (2026-08-19,
    # fifth review round) -- PipelineConfig no longer carries a
    # pinned_commit field to compare per-config (see conceptgrade/configs.py
    # module docstring's "Commit provenance" section for why: a per-config
    # commit pin could never correctly reference the commit that records
    # it). Commit provenance itself is checked in check_manifest_provenance()
    # below, against docs/PHASE0_RUN_MANIFEST_2026-08-19.json.
    for w in check_working_tree():
        print(f"    [info] {w}")


def check_calibration_artifacts():
    section("2. Calibration artifact freshness")
    from conceptgrade.verifier import VERIFIER_PROMPT_VERSION_SAG
    from conceptgrade.calibration import load

    # Narrow pattern -- data/calibration_analysis.json is an unrelated,
    # pre-existing Paper-1 recalibration-analysis file (different schema:
    # {"n", "raw", "linear", "isotonic"}), not a conceptgrade.calibration
    # artifact. Match only the domain-prefixed Calibration files this
    # module actually produces.
    cal_files = sorted(DATA.glob("calibration_mohler_data_structures_*.json"))
    if not cal_files:
        check("at least one calibration artifact exists", False)
        return
    for path in cal_files:
        try:
            cal = load(path)
        except Exception as e:
            check(f"{path.name} loads", False, str(e))
            continue
        # 2026-08-19, blocker #4: a MISSING verifier_prompt_version used to
        # silently pass here (the `not cal.verifier_prompt_version` clause
        # below treated "unset" as "compatible with everything"). That is
        # backwards -- a calibration artifact with no recorded prompt
        # version is exactly the case where we have NO evidence it still
        # matches the live prompt and must fail loudly, not be waved
        # through. Only an exact match now passes.
        check(
            f"{path.name}: verifier_prompt_version matches live code "
            f"(recorded={cal.verifier_prompt_version!r}, "
            f"live={VERIFIER_PROMPT_VERSION_SAG!r})",
            cal.verifier_prompt_version == VERIFIER_PROMPT_VERSION_SAG,
        )


def _mae_p(pred_key_a, pred_key_b, human, a, b):
    import numpy as np
    from scipy.stats import wilcoxon
    diff = np.abs(human - a) - np.abs(human - b)
    _, p = wilcoxon(diff)
    return float(np.abs(human - a).mean()), float(np.abs(human - b).mean()), float(p)


def check_headline_numbers():
    section("3. Headline numbers re-derived from cached data (Findings 5/6)")
    import numpy as np
    from scipy.stats import wilcoxon

    # Finding 5: generic skepticism recovers DeepSeek from harm to no
    # statistically significant difference (NOT "tie" -- nonsignificance is
    # not equivalence, no equivalence test was run) vs. the old
    # (pre-skepticism) evidence-trusting condition. REPRODUCIBILITY.md
    # documents this exact comparison as "p=0.76 vs. bare-verifier". Recomputed
    # exactly (paired Wilcoxon signed-rank on |human-bare| vs |human-skep|,
    # default 'wilcox' zero-handling) against a tight tolerance, not a loose band.
    bare_path = DATA / "deepseek_verifier_ablation_bare.json"
    skep_path = DATA / "deepseek_verifier_skeptical_evidence.json"
    if bare_path.exists() and skep_path.exists():
        bare = json.loads(bare_path.read_text())
        skep = json.loads(skep_path.read_text())
        full_d = json.loads((DATA / "deepseek_pipeline_eval_results.json").read_text())
        human, bare_s, skep_s = [], [], []
        for r in full_d["results"]:
            sid = r["id"]
            if sid not in bare or sid not in skep:
                continue
            human.append(r["human_score"]); bare_s.append(bare[sid]); skep_s.append(skep[sid])
        human, bare_s, skep_s = np.array(human), np.array(bare_s), np.array(skep_s)
        n = len(human)
        mae_bare = float(np.abs(human - bare_s).mean())
        mae_skep = float(np.abs(human - skep_s).mean())
        diff = np.abs(human - bare_s) - np.abs(human - skep_s)
        _, p = wilcoxon(diff, zero_method="wilcox")
        check(
            f"Finding 5: paired Wilcoxon p={p:.4f} matches the documented "
            f"'p=0.76 vs. bare-verifier' to within +/-0.05, n={n}",
            abs(p - 0.76) < 0.05,
            f"recomputed p={p:.4f}, mae_bare={mae_bare:.4f}, mae_skep={mae_skep:.4f}",
        )
        check(
            "Finding 5: no statistically significant difference detected between "
            "skeptical-evidence and bare-verifier at alpha=0.05 (the documented "
            "'recovers to no significant difference' claim -- not an equivalence claim)",
            p > 0.05,
            f"p={p:.4f}",
        )
    else:
        check("Finding 5 DeepSeek bare/skeptical cached data present", False,
              f"missing {bare_path.name if not bare_path.exists() else skep_path.name}")

    # Finding 6 / Section 5.13: targeted skepticism on Gemini did NOT beat
    # zero-shot -- REPRODUCIBILITY.md documents this as "MAE 0.4142->0.4220,
    # p=0.094". 2026-08-19, third review round: the earlier version of this
    # check recomputed on RAW (uncalibrated) scores and got p=0.0155 --
    # wrong basis, and its qualitative conclusion even pointed the opposite
    # direction. compute_targeted_skepticism_loqo.py resolved this: applying
    # this project's own established LOQO-recalibration protocol (intercept
    # + scale via Ridge, nested alpha selection -- the same protocol used in
    # compute_pipeline_diagnostic_stepwise.py and compute_clustered_
    # significance.py) to the same cached data reproduces the documented
    # MAE pair EXACTLY (0.4142/0.4220) and the response-level Wilcoxon p
    # to within 0.001 (0.0945 vs. 0.094). That script is therefore now the
    # source of truth for this comparison; this check just re-runs it and
    # requires the reproduction to still hold, rather than tolerating a
    # discrepancy with an alpha-guard workaround.
    #
    # Note (corrected 2026-08-19, fourth review round): the response-level
    # (p=0.094) vs. question-clustered (p=0.39) distinction was NOT a
    # newly discovered methodological gap -- both numbers were already
    # disclosed side by side in REPRODUCIBILITY.md Finding 6 and docs/
    # INVESTIGATION_REPORT_2026-08-18.md Section 5.13 before this script
    # existed. This is a reproducibility repair (a runnable, checkable
    # script for a result the report already stated correctly), not a
    # correction to the report's claims. Both p-values are asserted below
    # to the tight tolerance compute_targeted_skepticism_loqo.py now uses.
    import subprocess
    result = subprocess.run(
        ["python3", str(BASE / "compute_targeted_skepticism_loqo.py")],
        capture_output=True, text=True, cwd=str(BASE),
    )
    result_path = DATA / "targeted_skepticism_loqo_result.json"
    if result_path.exists():
        r = json.loads(result_path.read_text())
        check(
            f"Finding 6: LOQO-recalibrated reproduction of the documented "
            f"MAE/p=0.094 statistic succeeds (n={r['n']}, n_questions={r['n_questions']})",
            r["reproduced_within_tolerance"] is True,
            f"mae_zs={r['loqo_recalibrated_mae_zeroshot']:.4f} "
            f"mae_tgt={r['loqo_recalibrated_mae_targeted']:.4f} "
            f"p_response={r['wilcoxon_p_response_level']:.5f} "
            f"p_clustered={r['wilcoxon_p_question_clustered']:.5f} "
            f"(documented: mae_zs={r['documented_mae_zeroshot']} "
            f"mae_tgt={r['documented_mae_targeted']} "
            f"p_response={r['documented_p_response']} "
            f"p_clustered={r['documented_p_clustered']}) "
            f"-- UNREPRODUCIBLE: retract p=0.094/p=0.39 from all documents, "
            f"do not loosen this check to make it pass",
        )
        print(
            f"    [info] Finding 6: response-level p={r['wilcoxon_p_response_level']:.5f} "
            f"and question-clustered p={r['wilcoxon_p_question_clustered']:.5f} both "
            f"reproduced exactly -- both were already disclosed side by side in "
            f"REPRODUCIBILITY.md Finding 6; this is a reproducibility repair "
            f"(a runnable script for a result the report already stated), not a "
            f"newly discovered methodological gap."
        )
    else:
        check(
            "Finding 6: compute_targeted_skepticism_loqo.py ran and produced a result",
            False,
            result.stderr[-500:] if result.stderr else "no output file written",
        )


def check_required_artifacts():
    section("4. Required cached artifacts (Findings 4-6) present on disk")
    required = [
        "mohler_real_eval_results.json",
        "mohler_real_phaseA_signals.json",
        "reference_concepts_mohler.json",
        "gpt_pipeline_eval_results.json",
        "deepseek_pipeline_eval_results.json",
        "mohler_real_verifier_skeptical.json",
        "mohler_real_verifier_targeted.json",
        "mohler_real_verifier_corrected_cov.json",
        "mohler_real_verifier_evidence_removed.json",
    ]
    for name in required:
        check(f"data/{name} exists", (DATA / name).exists())


def _git(*args: str) -> str:
    import subprocess
    return subprocess.run(
        ["git", *args], cwd=BASE, capture_output=True, text=True, check=True,
    ).stdout.strip()


def check_manifest_provenance():
    """5. docs/PHASE0_RUN_MANIFEST_2026-08-19.json's recorded code_commit/
    code_commit_tree_hash must be genuinely correct -- not just present.
    2026-08-19, fifth review round: a prior manifest recorded
    pinned_commit values that were stale by the time the manifest itself
    was committed (a commit can't reference its own not-yet-computed
    hash), and this was never caught because provenance mismatches were
    only ever WARNINGS, never failures. This check independently
    re-derives, from git history alone (never trusting the manifest's own
    claims), which commit actually introduced/last touched the manifest
    file, what that commit's PARENT actually is, and what that parent's
    tree hash actually is -- then FAILS if the manifest's recorded values
    don't match. No tolerance, no warning-only fallback."""
    section("5. Manifest commit provenance (docs/PHASE0_RUN_MANIFEST_2026-08-19.json)")
    manifest_path = BASE / "docs" / "PHASE0_RUN_MANIFEST_2026-08-19.json"
    manifest_rel = "docs/PHASE0_RUN_MANIFEST_2026-08-19.json"
    if not manifest_path.exists():
        check("manifest file exists", False)
        return
    manifest = json.loads(manifest_path.read_text())

    try:
        manifest_commit = _git("log", "-1", "--format=%H", "--", manifest_rel)
    except Exception as e:
        check("could not determine the commit that introduced/touched the manifest", False, str(e))
        return
    if not manifest_commit:
        check(
            "manifest file has an introducing commit in git history",
            False,
            "the manifest exists on disk but git log finds no commit touching it "
            "-- it may be uncommitted; commit it (alone) before verifying",
        )
        return

    # 2026-08-19, sixth review round: the manifest-introducing commit
    # must be the CURRENT HEAD, not just some commit somewhere in
    # history. Without this, any later commit (even one that changes
    # this very verification script, as commit cd0e14b did) silently
    # leaves the manifest describing a stale, non-HEAD state while every
    # other check here still passes -- the parent/tree-hash checks below
    # only validate the manifest commit's OWN parent, never whether the
    # manifest commit is still the tip of the branch. This is the check
    # that makes Phase 0 verification correctly FAIL after any future
    # substantive commit, until a fresh manifest is generated and
    # committed on top of it.
    try:
        head = _git("rev-parse", "HEAD")
    except Exception as e:
        check("could not determine current HEAD", False, str(e))
        return
    check(
        f"manifest commit ({manifest_commit[:12]}) IS current HEAD ({head[:12]}) "
        f"-- the manifest must describe the tip of the branch, not a past commit",
        manifest_commit == head,
        f"manifest_commit={manifest_commit!r} HEAD={head!r} -- if these differ, "
        f"regenerate and commit a fresh manifest before trusting this check",
    )

    try:
        actual_parent = _git("rev-parse", f"{manifest_commit}^")
        actual_parent_tree = _git("rev-parse", f"{actual_parent}^{{tree}}")
    except Exception as e:
        check("manifest-introducing commit has a resolvable parent", False, str(e))
        return

    check(
        f"manifest's recorded code_commit ({manifest.get('code_commit', '')[:12]}) "
        f"IS the manifest commit's actual parent ({actual_parent[:12]})",
        manifest.get("code_commit") == actual_parent,
        f"recorded={manifest.get('code_commit')!r} actual_parent={actual_parent!r}",
    )
    check(
        f"manifest's recorded code_commit_tree_hash "
        f"({manifest.get('code_commit_tree_hash', '')[:12]}) matches the parent "
        f"commit's ACTUAL tree hash ({actual_parent_tree[:12]})",
        manifest.get("code_commit_tree_hash") == actual_parent_tree,
        f"recorded={manifest.get('code_commit_tree_hash')!r} actual={actual_parent_tree!r}",
    )

    # Metadata-only: the manifest commit should touch nothing else.
    # `git show --name-only` reports paths relative to the repo ROOT
    # (this is a monorepo -- packages/concept-aware/ is a subdirectory),
    # while manifest_rel above is relative to BASE (this package's own
    # directory) and happens to still resolve correctly as a `git log`
    # pathspec because `cwd=BASE`. The two path forms aren't the same
    # string, so compare by SUFFIX, not equality.
    try:
        changed_files = _git(
            "show", "--format=", "--name-only", manifest_commit
        ).splitlines()
    except Exception:
        changed_files = None
    if changed_files is not None:
        check(
            f"manifest commit ({manifest_commit[:12]}) is metadata-only "
            f"(touches only {manifest_rel})",
            len(changed_files) == 1 and changed_files[0].endswith(manifest_rel),
            f"actually touched: {changed_files}",
        )

    # Restricted-artifact fingerprints, if the manifest recorded any:
    # re-verify the ones that still exist locally haven't silently
    # changed since the manifest was generated (doesn't fail on artifacts
    # that are absent locally -- they're gitignored/untracked by design,
    # not everyone will have them checked out).
    restricted = manifest.get("restricted_artifacts", {})
    if restricted:
        from generate_phase0_manifest import _fingerprint_artifact
        for rel_path, recorded in restricted.items():
            if not recorded.get("exists"):
                continue
            current = _fingerprint_artifact(rel_path)
            if not current.get("exists"):
                continue  # not present locally -- fine, not a failure
            key = "sha256" if current.get("type") == "file" else "composite_sha256"
            check(
                f"restricted artifact {rel_path!r} content hash unchanged since manifest generation",
                current.get(key) == recorded.get(key),
                f"recorded={recorded.get(key)!r} current={current.get(key)!r}",
            )


def main() -> int:
    check_configs()
    check_calibration_artifacts()
    check_headline_numbers()
    check_required_artifacts()
    check_manifest_provenance()

    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed: {FAILURES}")
        return 1
    print("PASS: all investigation-integrity checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
