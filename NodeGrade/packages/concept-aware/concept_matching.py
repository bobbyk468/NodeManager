"""
Unified concept matching for batch prompt precomputation.

1. Keyword / description heuristics (fast, always available).
2. Optional semantic similarity via sentence-transformers (better for paraphrases).

Environment:
  CONCEPTGRADE_SEMANTIC=0   — disable embeddings even if installed
  CONCEPT_SIM_THRESHOLD     — cosine similarity threshold (default 0.40)
  SENTENCE_TRANSFORMER_MODEL — default all-MiniLM-L6-v2
  KG_MIN_COVERAGE           — min matched/expected ratio to show KG in C5 prompt (default 0.25)
"""

from __future__ import annotations

import os
from functools import lru_cache

import numpy as np

_DEFAULT_SIM_THRESHOLD = float(os.environ.get("CONCEPT_SIM_THRESHOLD", "0.40"))
_DEFAULT_SKLEARN_SIM_THRESHOLD = float(os.environ.get("SKLEARN_SIM_THRESHOLD", "0.10"))
_DEFAULT_KG_MIN_COVERAGE = float(os.environ.get("KG_MIN_COVERAGE", "0.25"))


def simple_concept_match(student_answer: str, kg_concepts: list[dict]) -> list[str]:
    """Match KG concepts using name/id tokens, description keywords, and id substrings."""
    matched: list[str] = []
    answer_lower = student_answer.lower()
    stop = {"the", "and", "for", "are", "that", "this", "with", "from", "not"}

    for c in kg_concepts:
        cid = c["id"]
        name = c.get("name", cid).lower()
        desc = c.get("description", "").lower()

        name_words = [w for w in name.replace("_", " ").split() if len(w) > 3]
        id_words = [w for w in cid.replace("_", " ").split() if len(w) > 3]
        all_kw = set(name_words + id_words)

        if any(w in answer_lower for w in all_kw):
            matched.append(cid)
            continue

        short_words = [w for w in name.replace("_", " ").split()
                       if len(w) > 2 and w not in stop]
        if short_words and any(w in answer_lower for w in short_words):
            matched.append(cid)
            continue

        if desc:
            desc_words = [w for w in desc.split() if len(w) > 4 and w not in stop]
            desc_hits = sum(1 for w in desc_words if w in answer_lower)
            if desc_hits >= 2:
                matched.append(cid)
                continue

        if cid.replace("_", " ") in answer_lower:
            matched.append(cid)

    return list(set(matched))


def _concept_text(c: dict) -> str:
    cid = c.get("id", "")
    name = c.get("name", cid)
    desc = c.get("description", "")
    return f"{name}. {desc}".strip()


@lru_cache(maxsize=1)
def _load_embedder():
    if os.environ.get("CONCEPTGRADE_SEMANTIC", "1").strip().lower() in ("0", "false", "no"):
        return None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    model_name = os.environ.get(
        "SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"
    )
    return SentenceTransformer(model_name)


def semantic_sklearn_match(
    student_answer: str,
    kg_concepts: list[dict],
    *,
    sim_threshold: float | None = None,
) -> list[str]:
    """
    Lightweight paraphrase signal: TF-IDF cosine between student answer and each
    concept line (no PyTorch). Uses sklearn only.
    """
    if not kg_concepts or not (student_answer or "").strip():
        return []
    thr = sim_threshold if sim_threshold is not None else _DEFAULT_SKLEARN_SIM_THRESHOLD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    eligible = [c for c in kg_concepts if _concept_text(c)]
    if not eligible:
        return []
    texts = [_concept_text(c) for c in eligible]
    try:
        vec = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=4096,
        )
        docs = [student_answer.strip()] + texts
        mat = vec.fit_transform(docs)
        sims = cosine_similarity(mat[0:1], mat[1:]).flatten()
    except Exception:
        return []
    out: list[str] = []
    for c, s in zip(eligible, sims, strict=True):
        if float(s) >= thr:
            out.append(c["id"])
    return out


def semantic_concept_match(
    student_answer: str,
    kg_concepts: list[dict],
    *,
    sim_threshold: float | None = None,
) -> list[str]:
    """Per-call embedding (slow); prefer ConceptEmbeddingCache for batches."""
    if not kg_concepts or not (student_answer or "").strip():
        return []
    model = _load_embedder()
    if model is None:
        return []
    thr = sim_threshold if sim_threshold is not None else _DEFAULT_SIM_THRESHOLD
    texts = [_concept_text(c) for c in kg_concepts]
    if not any(texts):
        return []
    emb_s = model.encode([student_answer.strip()], normalize_embeddings=True)
    emb_c = model.encode(texts, normalize_embeddings=True)
    sims = (emb_s @ emb_c.T).flatten()
    matched = []
    for c, s in zip(kg_concepts, sims, strict=True):
        if float(s) >= thr:
            matched.append(c["id"])
    return matched


def unified_concept_match(
    student_answer: str,
    kg_concepts: list[dict],
    *,
    sim_threshold: float | None = None,
    cache: ConceptEmbeddingCache | None = None,
) -> list[str]:
    """Union of keyword and semantic matches (embeddings if available, else TF-IDF)."""
    kw = set(simple_concept_match(student_answer, kg_concepts))
    sem: set[str] = set()
    if cache is not None and cache.active:
        sem |= set(cache.semantic_hits(student_answer, kg_concepts, sim_threshold))
    elif _load_embedder() is not None:
        sem |= set(
            semantic_concept_match(student_answer, kg_concepts, sim_threshold=sim_threshold)
        )
    else:
        # TF-IDF scale differs from embedding cosine; use SKLEARN_SIM_THRESHOLD only.
        sem |= set(semantic_sklearn_match(student_answer, kg_concepts))
    return list(kw | sem)


def coverage_ratio(matched: list[str], expected: list[str]) -> float:
    exp = [e for e in expected if e]
    if not exp:
        return 1.0 if matched else 0.0
    hit = len(set(matched) & set(exp))
    return hit / len(exp)


def should_use_kg_evidence(coverage: float, min_coverage: float | None = None) -> bool:
    m = min_coverage if min_coverage is not None else _DEFAULT_KG_MIN_COVERAGE
    return coverage >= m


class ConceptEmbeddingCache:
    """One encoder pass for all concepts appearing in any question KG."""

    def __init__(self, q_to_kg: dict[str, dict]):
        by_id: dict[str, dict] = {}
        for kg in q_to_kg.values():
            for c in kg.get("concepts", []):
                cid = c.get("id")
                if cid:
                    by_id[cid] = c
        self.by_id = by_id
        self.ids = list(by_id.keys())
        self.model = _load_embedder()
        self.emb: np.ndarray | None = None
        self.id_to_row: dict[str, int] = {}
        if self.model is not None and self.ids:
            texts = [_concept_text(by_id[i]) for i in self.ids]
            self.emb = np.asarray(
                self.model.encode(texts, normalize_embeddings=True), dtype=np.float32
            )
            self.id_to_row = {cid: i for i, cid in enumerate(self.ids)}

    @property
    def active(self) -> bool:
        return self.emb is not None and len(self.id_to_row) > 0

    def semantic_hits(
        self,
        student_answer: str,
        kg_concepts: list[dict],
        sim_threshold: float | None = None,
    ) -> list[str]:
        if not self.active or not (student_answer or "").strip():
            return []
        thr = sim_threshold if sim_threshold is not None else _DEFAULT_SIM_THRESHOLD
        eligible = [c for c in kg_concepts if c.get("id") in self.id_to_row]
        if not eligible:
            return []
        assert self.emb is not None
        rows = [self.id_to_row[c["id"]] for c in eligible]
        sub = self.emb[rows]
        emb_s = np.asarray(
            self.model.encode([student_answer.strip()], normalize_embeddings=True),
            dtype=np.float32,
        )
        sims = (emb_s @ sub.T).flatten()
        out = []
        for c, s in zip(eligible, sims, strict=True):
            if float(s) >= thr:
                out.append(c["id"])
        return out
