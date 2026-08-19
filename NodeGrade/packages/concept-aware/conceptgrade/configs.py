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

Commit provenance (2026-08-19, fifth review round -- removes a
self-reference cycle): `PipelineConfig` previously carried its own
`pinned_commit` field, fixed at authoring time. That field could never
correctly reference the commit that RECORDS a pin -- a commit cannot
contain its own not-yet-computed hash -- and every attempt to "fix" it
by re-pinning to a newer commit was itself a new commit, needing a new
pin, forever one commit behind. `pinned_commit` is REMOVED from
`PipelineConfig` entirely. Commit provenance now lives ONLY in
`docs/PHASE0_RUN_MANIFEST_2026-08-19.json`, which is generated to
reference an already-existing PARENT commit's exact SHA and tree hash,
then committed itself as a separate, metadata-only commit on top --
never referencing its own hash. `verify_investigation_integrity.py`
fails unless the manifest's recorded code commit is genuinely the
manifest commit's parent and the tree hash matches (see that script and
`generate_phase0_manifest.py`).

Three configs are provided as concrete named presets:
  - EVALUATED_MOHLER_GEMINI: what actually produced this project's
    reported Mohler evaluation numbers -- Gemini 2.5 Flash,
    self-consistency ON (3 runs, min 2 votes, 1.0s inter-run delay,
    matching run_real_eval_phaseA_signals.py exactly), generic
    Finding-5 skepticism, verifier_weight=1.0, frozen v1.0-expert KG.
    2026-08-19, fourth review round: a prior version of this module had
    NO config that actually matched the evaluated system --
    DEPLOYED_SAG_GEMINI recorded use_self_consistency=False while the
    real eval script used SelfConsistentExtractor. Use this config, not
    DEPLOYED_SAG_GEMINI, when reproducing or extending the Mohler
    evaluation.
  - DEPLOYED_SAG_GEMINI: the RUNTIME/DEFAULT configuration -- what a
    fresh pipeline construction gets with no self-consistency (matching
    ConceptGradePipeline's own class default, use_self_consistency=False,
    which uses one extraction call instead of three -- NOT "3x cheaper
    per response" overall, corrected 2026-08-19: the pipeline still makes
    several other LLM calls -- misconception/false-belief detection,
    cognitive-depth classification, the verifier -- so the total-cost
    ratio is smaller than 3x and hasn't been measured here). This is NOT
    what produced the reported evaluation numbers -- see
    EVALUATED_MOHLER_GEMINI above for that. Kept as a distinct config
    because a cheaper, no-self-consistency runtime path is a legitimate
    deployment choice, just not the one this project's own headline
    numbers were measured under.
  - C1_BASELINE_NO_EXTENSIONS: the pre-extensions ablation baseline
    (no self-consistency, no confidence weighting, no verifier) -- for
    ablation studies that specifically need the un-extended pipeline,
    NOT the accidental old class defaults this project shipped with
    before Finding 6.

Do NOT add a config here for targeted skepticism or any other
unvalidated experimental variant (REPRODUCIBILITY.md Finding 6) --
configs in this registry are meant to be things it's safe to build a
pipeline from, not a record of everything that was tried.

Fingerprinting (2026-08-19, fourth review round -- corrects a real bug):
`config_fingerprint()` hashes only the SEMANTIC fields that affect what
a pipeline actually computes or what a cache key should distinguish --
it explicitly EXCLUDES `name` and `description` (previously also
`pinned_commit`, before that field was removed entirely -- see the
"Commit provenance" section above). A prior version hashed every field
including `pinned_commit`, which meant re-pinning a config to a new
commit (pure provenance metadata, changes nothing about how the
pipeline runs) silently changed its cache fingerprint and therefore
every cache key built from it -- an unrelated commit-tracking edit was
invalidating caches as if it were a real configuration change. Commit
provenance now lives ONLY in the run manifest
(docs/PHASE0_RUN_MANIFEST_2026-08-19.json) -- never in `PipelineConfig`
itself, never in the semantic fingerprint that feeds
`pipeline.config_fingerprint` or any cache key.
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
    tree, evaluated fresh at call time. Never raises -- returns
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

    # Self-consistency parameters -- only meaningful when
    # use_self_consistency=True, but always recorded (not just the on/off
    # flag) so a config fully describes what "self-consistency" means for
    # it. 2026-08-19, fourth review round: added because DEPLOYED_SAG_GEMINI
    # previously had no way to record these at all, which hid the fact
    # that it didn't match the actually-evaluated system (see
    # EVALUATED_MOHLER_GEMINI below).
    sc_n_runs: int = 3
    sc_min_votes: int = 2
    sc_inter_run_delay: float = 0.0

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

    # No pinned_commit field here -- deliberately (2026-08-19, fifth
    # review round). A per-config commit pin can never correctly
    # reference the commit that records the pin, since that commit's
    # hash doesn't exist yet when the pin is written -- see the module
    # docstring's "Commit provenance" section. Commit provenance is
    # tracked exclusively in docs/PHASE0_RUN_MANIFEST_2026-08-19.json,
    # which references an already-existing parent commit and is itself
    # committed as a separate, later, metadata-only commit.


# Fields deliberately excluded from the SEMANTIC config fingerprint --
# neither changes what the pipeline computes or what a cache entry
# means, so neither may affect config_fingerprint() (2026-08-19, fourth
# review round; see module docstring's "Fingerprinting" section).
_NON_SEMANTIC_FIELDS = frozenset({"name", "description"})


def config_fingerprint(config: PipelineConfig) -> str:
    """Canonical hash of this config's SEMANTIC fields only -- every
    declared field EXCEPT `name` and `description` (see
    `_NON_SEMANTIC_FIELDS`). This is the "complete named configuration
    fingerprint" that build_pipeline() stamps onto the resulting
    pipeline (as `pipeline.config_fingerprint`) and that pipeline.py's
    cache keys fold in when a pipeline was built from a named config --
    so a config field this module doesn't (yet) individually enforce at
    build time, but which still describes the run (e.g.
    `calibration_domain`), is still reflected in what gets cached under
    it. Two configs with identical semantic flags but a different
    `name`/`description` get the SAME fingerprint (by design -- they'd
    produce identical pipeline behavior and should share a cache), and
    any edit to a semantic field changes the fingerprint automatically
    -- no separate version constant to remember to bump.

    Commit provenance is not, and has never been, part of this hash or
    of `PipelineConfig` at all -- see config_identity() and
    docs/PHASE0_RUN_MANIFEST_2026-08-19.json for where commit provenance
    is actually tracked."""
    from dataclasses import asdict
    from conceptgrade.cache import canonical_hash
    semantic = {k: v for k, v in asdict(config).items() if k not in _NON_SEMANTIC_FIELDS}
    return canonical_hash(semantic)


def config_identity(config: PipelineConfig) -> dict:
    """Human-facing view of a config: name, description, and its semantic
    fingerprint -- for the run manifest and reporting, NEVER for cache
    keys (config_fingerprint() above is what cache keys use). Contains
    no commit information -- PipelineConfig carries none; see the module
    docstring's "Commit provenance" section for why and where commit
    pinning actually lives (docs/PHASE0_RUN_MANIFEST_2026-08-19.json)."""
    return {
        "name": config.name,
        "description": config.description,
        "semantic_fingerprint": config_fingerprint(config),
    }


def check_working_tree() -> list[str]:
    """Returns a list of human-readable warnings (empty = clean) about the
    CURRENTLY checked-out working tree -- currently just whether it has
    uncommitted changes. Never raises. Takes no config argument (2026-08-19,
    fifth review round: this used to compare a config's now-removed
    pinned_commit field against live git state; that comparison is gone
    along with the field -- commit provenance is checked once, against
    the run manifest, not per-config; see
    verify_investigation_integrity.py)."""
    warnings = []
    _live_sha, live_dirty = _live_git_state()
    if live_dirty:
        warnings.append(
            "working tree has uncommitted changes -- a pipeline built "
            "now may not match what any pinned commit in the run "
            "manifest describes"
        )
    return warnings


def build_pipeline(config: PipelineConfig, api_key: str, strict_kg: bool = True):
    """Construct a ConceptGradePipeline from a named config, enforcing
    (not merely recording) verifier_prompt_version_sag, KG version, and
    provider/model consistency. Raises ConfigProvenanceError on any
    mismatch among those three. A dirty working tree is checked and
    printed as a warning, not raised -- common and expected during
    active development, but must never be silent (see
    check_working_tree())."""
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

    for w in check_working_tree():
        print(f"[configs] WARNING: {w}")

    kwargs = dict(
        api_key=api_key,
        model=config.model,
        use_self_consistency=config.use_self_consistency,
        use_confidence_weighting=config.use_confidence_weighting,
        use_llm_verifier=config.use_llm_verifier,
        use_sure_verifier=config.use_sure_verifier,
        verifier_weight=config.verifier_weight,
        sc_n_runs=config.sc_n_runs,
        sc_min_votes=config.sc_min_votes,
        sc_inter_run_delay=config.sc_inter_run_delay,
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


EVALUATED_MOHLER_GEMINI = PipelineConfig(
    name="evaluated_mohler_gemini",
    description=(
        "What actually produced this project's reported Mohler evaluation "
        "numbers -- matches run_real_eval_phaseA_signals.py's "
        "SelfConsistentExtractor(n_runs=3, min_votes=2, inter_run_delay=1.0) "
        "and run_real_eval_phaseB_batched.py's LLMVerifier(verifier_weight=1.0) "
        "exactly. Gemini 2.5 Flash backbone, self-consistency ON, verifier at "
        "weight=1.0 with the Finding-5 GENERIC skepticism prompt (NOT the "
        "unvalidated targeted variant -- see REPRODUCIBILITY.md Finding 6), "
        "frozen v1.0-expert KG (loaded from data/ds_knowledge_graph.json, "
        "NOT the live v1.1-expert builder). Use this config, not "
        "DEPLOYED_SAG_GEMINI, to reproduce or extend the Mohler evaluation --"
        "DEPLOYED_SAG_GEMINI has use_self_consistency=False and does NOT "
        "match what was actually run."
    ),
    model="gemini-2.5-flash",
    provider="google",
    verifier_prompt_version_sag="sag_v2_skepticism_2026-08-18",
    use_self_consistency=True,
    use_confidence_weighting=True,
    use_llm_verifier=True,
    verifier_weight=1.0,
    sc_n_runs=3,
    sc_min_votes=2,
    sc_inter_run_delay=1.0,
    kg_domain="data_structures",
    kg_version="1.0-expert",
    kg_snapshot_path="data/ds_knowledge_graph.json",
    extraction_confidence_threshold=0.70,
    calibration_path=None,  # per-deployment: pass the domain-matched calibration explicitly
    calibration_domain="mohler_data_structures",
)

DEPLOYED_SAG_GEMINI = PipelineConfig(
    name="deployed_sag_gemini",
    description=(
        "RUNTIME/DEFAULT configuration -- what a fresh pipeline gets with "
        "self-consistency OFF (matching ConceptGradePipeline's own class "
        "default: two fewer extraction calls than EVALUATED_MOHLER_GEMINI "
        "per response, not a measured 3x reduction in total cost -- the "
        "pipeline still makes several other LLM calls regardless of this "
        "flag). 2026-08-19, fourth review round: this config does NOT match what "
        "produced this project's reported Mohler evaluation numbers -- see "
        "EVALUATED_MOHLER_GEMINI above for that. Verifier at weight=1.0 "
        "with the Finding-5 GENERIC skepticism prompt (NOT the unvalidated "
        "targeted variant -- see REPRODUCIBILITY.md Finding 6), frozen "
        "v1.0-expert KG (loaded from data/ds_knowledge_graph.json, NOT the "
        "live v1.1-expert builder)."
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
)

REGISTRY: dict[str, PipelineConfig] = {
    c.name: c for c in [EVALUATED_MOHLER_GEMINI, DEPLOYED_SAG_GEMINI, C1_BASELINE_NO_EXTENSIONS]
}
