"""
conceptgrade/configs.py -- immutable, named experiment/deployment
configurations (2026-08-19, REPRODUCIBILITY.md Finding 6, Phase 0
integrity work; revised same day after a second external review found
the first version's KG-version and commit-provenance fields were
declared but not enforced).

Motivation: this project has repeatedly been burned by configuration
drift -- a caller instantiating `ConceptGradePipeline` with only some
arguments explicit gets whatever the class defaults happen to be at that
moment, which have changed at least twice this project's history
(verifier_weight 0.25 -> 1.0; use_llm_verifier False -> True). A results
table, a paper claim, or a deployed grading run should be traceable to
one specific, named, versioned configuration -- not to "whatever the
defaults were on the day this script ran," and not to a config object
whose declared fields are decorative rather than enforced.

Each `PipelineConfig` here is a frozen dataclass. `build_pipeline()`
ENFORCES every field that can change what a pipeline run actually
computes:
  - `kg_snapshot_path` is loaded via `DomainKnowledgeGraph.load()` and
    its resulting `.version` is checked against `kg_version` -- it does
    NOT fall through to the live `build_data_structures_graph()`
    builder, which currently produces "1.1-expert", not "1.0-expert"
    (see README.md's warning about not overwriting the frozen KG
    snapshot). A config that declares kg_version="1.0" but doesn't
    supply a matching snapshot path fails loudly rather than silently
    building a different graph.
  - `provider` is checked against `model` for the known naming
    conventions this project's `conceptgrade.llm_client.detect_provider`
    actually uses (a model with "/" routes through OpenRouter regardless
    of declared provider; "gemini*" implies google; etc.) -- a mismatch
    fails loudly.
  - `verifier_prompt_version_sag` is checked against the live
    `conceptgrade.verifier.VERIFIER_PROMPT_VERSION_SAG` constant (as in
    the first version of this module).
  - `pinned_commit` is a FIXED string recorded once, at authoring time,
    NOT recomputed dynamically on every import (the first version's
    `default_factory` did this, which meant "the same named config"
    silently reported a different commit on every subsequent commit --
    defeating the point of pinning). `check_provenance()` compares the
    pinned value against the CURRENT live commit/dirty-state and reports
    (does not silently ignore) any mismatch; `build_pipeline()` calls it
    and prints a warning (does not raise -- a mismatch is expected and
    fine during active development, but must never be silent).

Two configs are provided as concrete named presets:
  - DEPLOYED_SAG_GEMINI: what this project's evaluation results actually
    use (Gemini 2.5 Flash, generic Finding-5 skepticism, verifier_weight=1.0,
    frozen v1.0-expert KG).
  - C1_BASELINE_NO_EXTENSIONS: the pre-extensions ablation baseline
    (no self-consistency, no confidence weighting, no verifier) -- for
    ablation studies that specifically need the un-extended pipeline,
    NOT the accidental old class defaults this project shipped with
    before Finding 6.

Do NOT add a config here for targeted skepticism or any other
unvalidated experimental variant (REPRODUCIBILITY.md Finding 6) --
configs in this registry are meant to be things it's safe to build a
pipeline from, not a record of everything that was tried.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent


class ConfigProvenanceError(Exception):
    """Raised by build_pipeline() when a config's declared fields don't
    match what the code would actually produce (wrong KG version loaded,
    provider/model mismatch, stale prompt version) -- never silently
    proceeds with a mismatch on any of these three."""


def _live_git_state() -> tuple[str, bool]:
    """(current short commit SHA, is_dirty) for the CURRENTLY checked-out
    tree, evaluated fresh at call time (unlike PipelineConfig.pinned_commit,
    which is a fixed value recorded once). Never raises -- returns
    ("unknown", True) if git isn't available."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=5,
        ).stdout.strip())
        return (sha or "unknown", dirty)
    except Exception:
        return ("unknown", True)


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable. Every field here is enforced by build_pipeline(), not
    merely recorded -- see module docstring."""
    name: str                                  # e.g. "deployed_sag_gemini"
    description: str

    # Model / provider -- provider is checked against model at build time
    model: str
    provider: str                              # "google" | "openrouter" | ...

    # Prompt versions -- checked against the live constant at build time
    verifier_prompt_version_sag: str

    # Extension flags
    use_self_consistency: bool
    use_confidence_weighting: bool
    use_llm_verifier: bool
    verifier_weight: float
    use_sure_verifier: bool = False
    use_hierarchical_kg: bool = False

    # KG identity -- kg_snapshot_path is loaded and its version checked
    # against kg_version at build time. A config with kg_version set but
    # kg_snapshot_path=None cannot be built (fails loudly rather than
    # silently using the live, drifted KG builder).
    kg_domain: str = "data_structures"
    kg_version: str = "1.0-expert"
    kg_snapshot_path: Optional[str] = "data/ds_knowledge_graph.json"

    # Extraction
    extraction_confidence_threshold: float = 0.70

    # Calibration (None = uncalibrated)
    calibration_path: Optional[str] = None
    calibration_domain: str = ""

    # Provenance: FIXED at authoring time, not recomputed dynamically.
    # A config with pinned_commit="unpinned" has deliberately not been
    # pinned yet (e.g. authored mid-session before a commit exists) --
    # check_provenance() treats that as informational, not an error.
    pinned_commit: str = "unpinned"


def config_fingerprint(config: PipelineConfig) -> str:
    """Canonical hash of every declared field on this config (2026-08-19,
    third review round). This is the "complete named configuration
    fingerprint" that build_pipeline() stamps onto the resulting pipeline
    (as `pipeline.config_fingerprint`) and that pipeline.py's cache keys
    fold in when a pipeline was built from a named config -- so a config
    field this module doesn't (yet) individually enforce at build time,
    but which still describes the run (e.g. `description`, `calibration_domain`),
    is still reflected in what gets cached under it. Two configs with
    identical individual flags but a different `name`/`description` get
    different fingerprints, and any edit to a config's fields changes its
    fingerprint automatically -- no separate version constant to remember
    to bump."""
    from dataclasses import asdict
    from conceptgrade.cache import canonical_hash
    return canonical_hash(asdict(config))


def check_provenance(config: PipelineConfig) -> list[str]:
    """Returns a list of human-readable warnings (empty = clean) comparing
    `config.pinned_commit` against the CURRENTLY checked-out commit/dirty
    state. Never raises, never silently returns nothing to check --
    callers (build_pipeline, verify_investigation_integrity.py) are
    responsible for surfacing the returned warnings."""
    warnings = []
    live_sha, live_dirty = _live_git_state()
    if config.pinned_commit == "unpinned":
        warnings.append(
            f"config {config.name!r} has no pinned_commit -- provenance "
            f"cannot be checked against a known-good commit"
        )
    elif config.pinned_commit != live_sha:
        warnings.append(
            f"config {config.name!r} is pinned to commit "
            f"{config.pinned_commit!r} but the working tree is currently "
            f"at {live_sha!r} -- results produced now are NOT necessarily "
            f"what this config originally described"
        )
    if live_dirty:
        warnings.append(
            f"working tree has uncommitted changes -- even a matching "
            f"pinned_commit does not guarantee the code matches what ran "
            f"when config {config.name!r} was authored"
        )
    return warnings


def build_pipeline(config: PipelineConfig, api_key: str, strict_kg: bool = True):
    """Construct a ConceptGradePipeline from a named config, enforcing
    (not merely recording) verifier_prompt_version_sag, KG version, and
    provider/model consistency. Raises ConfigProvenanceError on any
    mismatch among those three. Provenance (pinned_commit vs. live git
    state) is checked and printed as warnings, not raised -- a mismatch
    there is common and expected during active development, but must
    never be silent (see check_provenance())."""
    from conceptgrade.pipeline import ConceptGradePipeline
    from conceptgrade.verifier import VERIFIER_PROMPT_VERSION_SAG
    from conceptgrade.llm_client import detect_provider
    from knowledge_graph.domain_graph import DomainKnowledgeGraph

    if config.verifier_prompt_version_sag != VERIFIER_PROMPT_VERSION_SAG:
        raise ConfigProvenanceError(
            f"Config {config.name!r} records verifier_prompt_version_sag="
            f"{config.verifier_prompt_version_sag!r}, but the live "
            f"conceptgrade.verifier.VERIFIER_PROMPT_VERSION_SAG is "
            f"{VERIFIER_PROMPT_VERSION_SAG!r}. This config is stale -- "
            f"update it (and re-validate anything that depended on it) "
            f"before using it."
        )

    detected = detect_provider(config.model)
    if detected != config.provider:
        raise ConfigProvenanceError(
            f"Config {config.name!r} declares provider={config.provider!r} "
            f"for model={config.model!r}, but "
            f"conceptgrade.llm_client.detect_provider() resolves this "
            f"model to provider={detected!r}. The config's declared "
            f"provider does not match what will actually be called."
        )

    domain_graph = None
    if strict_kg:
        if not config.kg_snapshot_path:
            raise ConfigProvenanceError(
                f"Config {config.name!r} declares kg_version="
                f"{config.kg_version!r} but no kg_snapshot_path -- "
                f"without an explicit snapshot to load, the pipeline "
                f"would fall through to ConceptGradePipeline's default "
                f"live KG builder, which currently produces "
                f"'1.1-expert', not {config.kg_version!r} (see README.md's "
                f"warning about not overwriting the frozen KG snapshot). "
                f"Set kg_snapshot_path or pass strict_kg=False if this "
                f"is deliberate."
            )
        snapshot_path = _REPO_ROOT / config.kg_snapshot_path
        domain_graph = DomainKnowledgeGraph.load(snapshot_path)
        if domain_graph.version != config.kg_version:
            raise ConfigProvenanceError(
                f"Config {config.name!r} declares kg_version="
                f"{config.kg_version!r}, but loading "
                f"{config.kg_snapshot_path!r} produced a graph with "
                f".version={domain_graph.version!r}. The config's "
                f"declared KG version does not match the snapshot it "
                f"points to."
            )

    for w in check_provenance(config):
        print(f"[configs] WARNING: {w}")

    kwargs = dict(
        api_key=api_key,
        model=config.model,
        use_self_consistency=config.use_self_consistency,
        use_confidence_weighting=config.use_confidence_weighting,
        use_llm_verifier=config.use_llm_verifier,
        use_sure_verifier=config.use_sure_verifier,
        verifier_weight=config.verifier_weight,
        use_hierarchical_kg=config.use_hierarchical_kg,
        extraction_confidence_threshold=config.extraction_confidence_threshold,
        domain=config.calibration_domain,
    )
    if domain_graph is not None:
        kwargs["domain_graph"] = domain_graph
    if config.calibration_path is not None:
        kwargs["calibration_path"] = config.calibration_path
    pipeline = ConceptGradePipeline(**kwargs)
    # Stamp the config identity onto the built pipeline so its cache keys
    # can fold in the complete configuration fingerprint, not just the
    # individual flags build_pipeline() happens to enforce today.
    pipeline.config_name = config.name
    pipeline.config_fingerprint = config_fingerprint(config)
    return pipeline


DEPLOYED_SAG_GEMINI = PipelineConfig(
    name="deployed_sag_gemini",
    description=(
        "This project's actual deployed/evaluated configuration for SAG "
        "(short-answer) grading: Gemini 2.5 Flash backbone, verifier at "
        "weight=1.0 with the Finding-5 GENERIC skepticism prompt (NOT the "
        "unvalidated targeted variant -- see REPRODUCIBILITY.md Finding 6), "
        "frozen v1.0-expert KG (loaded from data/ds_knowledge_graph.json, "
        "NOT the live v1.1-expert builder)."
    ),
    model="gemini-2.5-flash",
    provider="google",
    verifier_prompt_version_sag="sag_v2_skepticism_2026-08-18",
    use_self_consistency=False,
    use_confidence_weighting=True,
    use_llm_verifier=True,
    verifier_weight=1.0,
    kg_domain="data_structures",
    kg_version="1.0-expert",
    kg_snapshot_path="data/ds_knowledge_graph.json",
    extraction_confidence_threshold=0.70,
    calibration_path=None,  # per-deployment: pass the domain-matched calibration explicitly
    calibration_domain="mohler_data_structures",
    pinned_commit="e4cffa7",  # Phase 0 integrity commit -- see docs/PHASE0_RUN_MANIFEST_2026-08-19.json
)

C1_BASELINE_NO_EXTENSIONS = PipelineConfig(
    name="c1_baseline_no_extensions",
    description=(
        "Ablation-study baseline: no self-consistency, no confidence "
        "weighting, no LLM verifier -- pure KG-formula scoring. This is "
        "the config the un-extended C1 ablation condition should use "
        "explicitly, rather than relying on ConceptGradePipeline's class "
        "defaults (which changed 2026-08-18 to match the DEPLOYED config "
        "above, not this baseline -- see REPRODUCIBILITY.md Finding 4)."
    ),
    model="gemini-2.5-flash",
    provider="google",
    verifier_prompt_version_sag="sag_v2_skepticism_2026-08-18",  # informational; verifier unused here
    use_self_consistency=False,
    use_confidence_weighting=False,
    use_llm_verifier=False,
    verifier_weight=0.0,
    kg_domain="data_structures",
    kg_version="1.0-expert",
    kg_snapshot_path="data/ds_knowledge_graph.json",
    extraction_confidence_threshold=0.70,
    calibration_path=None,
    calibration_domain="",
    pinned_commit="e4cffa7",  # Phase 0 integrity commit -- see docs/PHASE0_RUN_MANIFEST_2026-08-19.json
)

REGISTRY: dict[str, PipelineConfig] = {
    c.name: c for c in [DEPLOYED_SAG_GEMINI, C1_BASELINE_NO_EXTENSIONS]
}
