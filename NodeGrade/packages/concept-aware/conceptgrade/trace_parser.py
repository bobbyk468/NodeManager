"""
Stage 3b — Trace Parser.

Converts the raw <think> reasoning trace produced by a Large Reasoning Model
(e.g., DeepSeek-R1-Distill-Llama-3-70B) into a structured list of KG-linked,
classified reasoning steps suitable for visual rendering in the
VerifierReasoningPanel dashboard component.

Pipeline position
-----------------
Stage 3a  LRM-as-Verifier  →  raw <think> trace  +  {"valid": bool, "reasoning": str}
Stage 3b  TraceParser      →  [ParsedStep, ...]   (structured, KG-linked, classified)
Stage 4   Chain Coverage   →  coverage %

Output schema (one ParsedStep per sentence kept)
-------------------------------------------------
{
    "step_id":           int,          # 1-based index in the final kept sequence
    "text":              str,          # cleaned sentence text
    "classification":    str,          # "SUPPORTS" | "CONTRADICTS" | "UNCERTAIN"
    "kg_nodes":          [str],        # KG node IDs referenced in this step
    "kg_edges":          [str],        # KG edge types referenced in this step
    "confidence_delta":  float,        # +/- impact on edge confidence weights
    "is_conclusion":     bool,         # True for the final-resolution sentences
}

Algorithm
---------
1. Strip <think>…</think> wrapper; extract raw trace text.
2. Sentence-segment the trace.
3. Filter exploratory branches (hypothesis-testing, self-corrections, questions).
4. KG entity link: fuzzy-match each sentence against KG node labels and edge types.
5. Classify: keyword pattern matching → SUPPORTS / CONTRADICTS / UNCERTAIN.
6. Assign confidence_delta: SUPPORTS +0.1, CONTRADICTS −0.15, UNCERTAIN 0.0.
7. Mark conclusion sentences (last cluster of non-exploratory steps).
8. Return structured list sorted by step_id.

Design rationale
----------------
All operations are deterministic Python (no additional model calls).
The Trace Parser is itself a research contribution: it transforms an
unstructured wall of LRM text into a structured artifact that can be
rendered as a CMV-linked visual in the React dashboard (see VAST §IV.D).
"""

from __future__ import annotations

import re
import difflib
from dataclasses import dataclass, field
from typing import Optional


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class ParsedStep:
    step_id: int
    text: str
    classification: str          # "SUPPORTS" | "CONTRADICTS" | "UNCERTAIN"
    kg_nodes: list[str]
    kg_edges: list[str]
    confidence_delta: float
    is_conclusion: bool

    def to_dict(self) -> dict:
        return {
            "step_id":          self.step_id,
            "text":             self.text,
            "classification":   self.classification,
            "kg_nodes":         self.kg_nodes,
            "kg_edges":         self.kg_edges,
            "confidence_delta": round(self.confidence_delta, 3),
            "is_conclusion":    self.is_conclusion,
        }


# ── Classification keyword lists ──────────────────────────────────────────────

_SUPPORTS_PATTERNS = re.compile(
    r'\b(correct(?:ly)?|identif(?:ies|ied)|mentions?|demonstrates?|confirms?|'
    r'includes?|addresses?|captures?|recognizes?|appropriately|shows?|'
    r'establishes?|verif(?:ies|ied)|valid|sound|accurate|present|covers?|'
    r'successfully|right(?:ly)?|good|strong|clear(?:ly)?)\b',
    re.IGNORECASE,
)

_CONTRADICTS_PATTERNS = re.compile(
    r'\b(fail(?:s|ed)?|missing|miss(?:es|ed)|incorrect(?:ly)?|wrong(?:ly)?|'
    r'omit(?:s|ted)?|lack(?:s|ed)?|absent|ignores?|overlooks?|does\s+not|'
    r'doesn\'t|did\s+not|didn\'t|cannot|can\'t|never|no\s+mention|'
    r'completely\s+fails?|entirely\s+miss(?:es|ed)?|not\s+address|'
    r'not\s+demonstrat|insufficient|inadequate|incorrect|false|error(?:s|eous)?|'
    r'contradicts?|inconsistent)\b',
    re.IGNORECASE,
)

_UNCERTAIN_PATTERNS = re.compile(
    r'\b(implies?|implied|implication|weak(?:ly)?|partial(?:ly)?|unclear|'
    r'ambiguous|somewhat|vague(?:ly)?|limited|may\b|might\b|could\b|'
    r'possibly|perhaps|seem(?:s|ed)?|appear(?:s|ed)?|suggest(?:s|ed)?|'
    r'indirect(?:ly)?|implicit(?:ly)?|not\s+explicit|loosely|borderline|'
    r'moderate(?:ly)?|debatable|questionable)\b',
    re.IGNORECASE,
)

# Confidence deltas per classification
_DELTA = {
    "SUPPORTS":    +0.10,
    "CONTRADICTS": -0.15,
    "UNCERTAIN":    0.00,
}

# ── Exploratory branch markers ────────────────────────────────────────────────
# These sentence patterns indicate hypothesis-testing or self-correction — they
# should be discarded so the dashboard only shows the final conclusion path.

_EXPLORATORY_PATTERNS = re.compile(
    r'^\s*('
    r'wait[,.]?|actually[,.]?|hmm[,.]?|hm[,.]?|let me|let\'s see|'
    r'no wait|let me reconsider|let me re-?read|let me think|'
    r'on second thought|come to think|going back|re-?consider|'
    r'scratch that|never mind|i was wrong|i made an error|'
    r'hold on|actually,?\s+no|actually,?\s+yes|'
    r'first,?\s+let me|ok(?:ay)?,?\s+so|right,?\s+so|'
    r'so,?\s+to\s+summarize|to\s+be\s+clear'
    r')',
    re.IGNORECASE,
)

_QUESTION_RE = re.compile(r'\?\s*$')

_HYPOTHESIS_RE = re.compile(
    r'\b(suppose|assuming|if\s+we\s+assume|hypothetically|'
    r'what\s+if|let\'s\s+say|for\s+the\s+sake\s+of)\b',
    re.IGNORECASE,
)


# ── KG entity linker ──────────────────────────────────────────────────────────

_FUZZY_THRESHOLD = 0.72   # SequenceMatcher ratio cutoff for fuzzy node matching
_EDGE_TYPE_ALIASES: dict[str, list[str]] = {
    "PREREQUISITE_FOR":   ["prerequisite", "required for", "needed for", "precedes", "requires"],
    "HAS_PROPERTY":       ["has property", "property of", "characterized by", "defined by"],
    "IMPLEMENTS":         ["implements", "realizes", "uses", "applies"],
    "PRODUCES":           ["produces", "results in", "leads to", "causes", "outputs"],
    "OPERATES_ON":        ["operates on", "works on", "acts on", "applied to"],
    "CONTRASTS_WITH":     ["contrasts with", "differs from", "unlike", "opposite of", "versus"],
    "HAS_PART":           ["has part", "consists of", "contains", "part of", "component of"],
    "VARIANT_OF":         ["variant of", "type of", "kind of", "form of", "subtype"],
}


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation for matching."""
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower()).strip()


def _link_nodes(sentence: str, kg_nodes: list[str]) -> list[str]:
    """
    Return KG node IDs that are referenced in the sentence.

    Uses two passes:
      1. Direct substring match (lowercased, underscore→space normalized).
      2. Fuzzy SequenceMatcher for short variants (e.g., "gradient" → "gradient_descent").
    """
    norm_sent = _normalize(sentence)
    matched: list[str] = []

    for node_id in kg_nodes:
        # Normalise node_id (underscores → spaces, lowercase)
        node_label = _normalize(node_id.replace('_', ' '))

        # Pass 1: substring
        if node_label in norm_sent:
            matched.append(node_id)
            continue

        # Pass 2: any word in the node label appears as a standalone word in sentence
        node_words = [w for w in node_label.split() if len(w) > 3]
        if any(re.search(rf'\b{re.escape(w)}\b', norm_sent) for w in node_words):
            matched.append(node_id)
            continue

        # Pass 3: fuzzy ratio on the whole node label
        ratio = difflib.SequenceMatcher(None, node_label, norm_sent).ratio()
        # Weight by proportion of sentence covered
        if ratio > _FUZZY_THRESHOLD and len(node_label) >= 6:
            matched.append(node_id)

    return matched


def _link_edges(sentence: str, kg_edge_types: list[str]) -> list[str]:
    """Return edge type keys from the KG that are semantically referenced in the sentence."""
    norm_sent = _normalize(sentence)
    matched: list[str] = []

    for edge_type in kg_edge_types:
        # Check aliases defined above
        aliases = _EDGE_TYPE_ALIASES.get(edge_type, [])
        canonical = _normalize(edge_type.replace('_', ' '))
        candidates = [canonical] + [_normalize(a) for a in aliases]
        if any(c in norm_sent for c in candidates):
            matched.append(edge_type)

    return matched


# ── Sentence segmenter ────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences.
    Handles common abbreviations to avoid false splits (e.g., "e.g.", "i.e.", "etc.").
    """
    # Protect common abbreviations
    text = re.sub(r'\b(e\.g|i\.e|etc|vs|Dr|Mr|Mrs|Prof|Fig|Eq|Sec|cf)\.',
                  lambda m: m.group().replace('.', '⟨DOT⟩'), text)

    # Split on sentence boundaries: period/exclamation/question followed by space+capital
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\"])', text)

    # Restore protected dots
    sentences = [s.replace('⟨DOT⟩', '.').strip() for s in sentences]

    # Also split on newlines that likely separate reasoning steps
    expanded: list[str] = []
    for sent in sentences:
        sub = [s.strip() for s in re.split(r'\n{2,}', sent) if s.strip()]
        expanded.extend(sub if sub else [sent])

    return [s for s in expanded if len(s) > 10]


# ── Exploratory branch filter ─────────────────────────────────────────────────

def _is_exploratory(sentence: str) -> bool:
    """
    Return True if the sentence is a hypothesis-testing, self-correction,
    or question sentence that should be discarded from the final trace.
    """
    if _QUESTION_RE.search(sentence):
        return True
    if _EXPLORATORY_PATTERNS.match(sentence):
        return True
    if _HYPOTHESIS_RE.search(sentence):
        return True
    return False


# ── Classifier ───────────────────────────────────────────────────────────────

def _classify(sentence: str) -> str:
    """
    Return SUPPORTS / CONTRADICTS / UNCERTAIN based on keyword presence.
    Priority: CONTRADICTS > SUPPORTS > UNCERTAIN (negations dominate).
    """
    has_contra   = bool(_CONTRADICTS_PATTERNS.search(sentence))
    has_supports = bool(_SUPPORTS_PATTERNS.search(sentence))
    has_uncertain = bool(_UNCERTAIN_PATTERNS.search(sentence))

    # A sentence with BOTH supports and contradicts keywords leans CONTRADICTS
    # (e.g., "correctly identifies X but misses Y")
    if has_contra:
        return "CONTRADICTS"
    if has_supports:
        return "SUPPORTS"
    if has_uncertain:
        return "UNCERTAIN"
    return "UNCERTAIN"   # Default for opaque sentences


# ── Conclusion marker ─────────────────────────────────────────────────────────

def _mark_conclusions(steps: list[dict]) -> list[dict]:
    """
    Mark the final cluster of kept steps as conclusions.
    Heuristic: last N steps where N = max(1, len(steps) // 4).
    Additionally, steps containing explicit conclusion phrases are always marked.
    """
    conclusion_phrases = re.compile(
        r'\b(therefore|thus|in\s+conclusion|overall|in\s+summary|'
        r'to\s+summarize|hence|finally|as\s+a\s+result|'
        r'this\s+means|consequently|so\s+the\s+answer)\b',
        re.IGNORECASE,
    )
    n = len(steps)
    tail_size = max(1, n // 4)
    tail_start = n - tail_size

    for i, step in enumerate(steps):
        step["is_conclusion"] = (
            i >= tail_start
            or bool(conclusion_phrases.search(step["text"]))
        )
    return steps


# ── Extract <think> block ─────────────────────────────────────────────────────

def _extract_think_block(raw_output: str) -> str:
    """
    Extract content between <think>…</think> tags.
    If no tags found, treat the entire output as the trace.
    """
    match = re.search(r'<think>(.*?)</think>', raw_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # No tags — check if there's a JSON block at the end; strip it
    json_start = raw_output.rfind('{')
    if json_start > 100:
        return raw_output[:json_start].strip()
    return raw_output.strip()


# ── Public API ────────────────────────────────────────────────────────────────

def parse_trace(
    raw_lrm_output: str,
    kg_nodes: list[str],
    kg_edge_types: Optional[list[str]] = None,
    max_steps: int = 20,
) -> list[dict]:
    """
    Parse a raw LRM output (including optional <think> block) into a structured
    list of KG-linked, classified reasoning steps.

    Parameters
    ----------
    raw_lrm_output : str
        Full output from the LRM, may include <think>…</think> wrapper.
    kg_nodes : list[str]
        List of node IDs from the rubric KG (e.g., ["gradient_descent", "learning_rate"]).
    kg_edge_types : list[str], optional
        List of edge type strings from the KG (e.g., ["PREREQUISITE_FOR", "PRODUCES"]).
        Defaults to all keys in _EDGE_TYPE_ALIASES.
    max_steps : int
        Maximum number of parsed steps to return (keeps the most informative).
        Default 20 — enough for a dashboard panel without overwhelming the educator.

    Returns
    -------
    list[dict]
        List of ParsedStep dicts (see module docstring for schema).
        Empty list if the trace is too short or entirely exploratory.
    """
    if kg_edge_types is None:
        kg_edge_types = list(_EDGE_TYPE_ALIASES.keys())

    # Step 1: extract trace text
    trace_text = _extract_think_block(raw_lrm_output)
    if not trace_text:
        return []

    # Step 2: sentence segmentation
    sentences = _split_sentences(trace_text)

    # Step 3: filter exploratory branches
    kept = [s for s in sentences if not _is_exploratory(s)]

    if not kept:
        # Fallback: if everything was filtered, keep non-question sentences
        kept = [s for s in sentences if not _QUESTION_RE.search(s)]

    # Step 4–6: entity link + classify + delta
    raw_steps: list[dict] = []
    for sent in kept:
        nodes = _link_nodes(sent, kg_nodes)
        edges = _link_edges(sent, kg_edge_types)
        cls   = _classify(sent)
        delta = _DELTA[cls]

        raw_steps.append({
            "text":              sent,
            "classification":    cls,
            "kg_nodes":          nodes,
            "kg_edges":          edges,
            "confidence_delta":  delta,
            "is_conclusion":     False,
        })

    # Step 7: mark conclusion cluster
    raw_steps = _mark_conclusions(raw_steps)

    # Step 8: trim to max_steps, prioritising conclusions + contradicts
    #         (most informative for educators)
    if len(raw_steps) > max_steps:
        conclusions  = [s for s in raw_steps if s["is_conclusion"]]
        contradicts  = [s for s in raw_steps if not s["is_conclusion"] and s["classification"] == "CONTRADICTS"]
        supports     = [s for s in raw_steps if not s["is_conclusion"] and s["classification"] == "SUPPORTS"]
        uncertain    = [s for s in raw_steps if not s["is_conclusion"] and s["classification"] == "UNCERTAIN"]

        # Fill budget: conclusions first, then contradicts, then supports, then uncertain
        selected: list[dict] = []
        budget = max_steps
        for pool in [conclusions, contradicts, supports, uncertain]:
            take = pool[:budget]
            selected.extend(take)
            budget -= len(take)
            if budget <= 0:
                break

        # Re-sort by original order (preserves narrative flow)
        original_order = {id(s): i for i, s in enumerate(raw_steps)}
        selected.sort(key=lambda s: original_order.get(id(s), 9999))
        raw_steps = selected

    # Step 9: assign final step_ids (1-based)
    result: list[dict] = []
    for i, step in enumerate(raw_steps, start=1):
        result.append(ParsedStep(
            step_id          = i,
            text             = step["text"],
            classification   = step["classification"],
            kg_nodes         = step["kg_nodes"],
            kg_edges         = step["kg_edges"],
            confidence_delta = step["confidence_delta"],
            is_conclusion    = step["is_conclusion"],
        ).to_dict())

    return result


def summarise_trace(parsed_steps: list[dict]) -> dict:
    """
    Produce a compact summary of the parsed trace for the dashboard ClassSummaryCard.

    Returns
    -------
    dict with keys:
        total_steps      : int
        supports_count   : int
        contradicts_count: int
        uncertain_count  : int
        net_delta        : float   (sum of all confidence_delta values)
        conclusion_text  : str     (text of the last is_conclusion=True step, or "")
        nodes_referenced : list[str]  (deduplicated, sorted)
        edges_referenced : list[str]  (deduplicated, sorted)
    """
    if not parsed_steps:
        return {
            "total_steps": 0, "supports_count": 0, "contradicts_count": 0,
            "uncertain_count": 0, "net_delta": 0.0,
            "conclusion_text": "", "nodes_referenced": [], "edges_referenced": [],
        }

    supports    = [s for s in parsed_steps if s["classification"] == "SUPPORTS"]
    contradicts = [s for s in parsed_steps if s["classification"] == "CONTRADICTS"]
    uncertain   = [s for s in parsed_steps if s["classification"] == "UNCERTAIN"]
    conclusions = [s for s in parsed_steps if s["is_conclusion"]]

    all_nodes = sorted(set(n for s in parsed_steps for n in s["kg_nodes"]))
    all_edges = sorted(set(e for s in parsed_steps for e in s["kg_edges"]))
    net_delta = round(sum(s["confidence_delta"] for s in parsed_steps), 3)

    return {
        "total_steps":       len(parsed_steps),
        "supports_count":    len(supports),
        "contradicts_count": len(contradicts),
        "uncertain_count":   len(uncertain),
        "net_delta":         net_delta,
        "conclusion_text":   conclusions[-1]["text"] if conclusions else "",
        "nodes_referenced":  all_nodes,
        "edges_referenced":  all_edges,
    }
