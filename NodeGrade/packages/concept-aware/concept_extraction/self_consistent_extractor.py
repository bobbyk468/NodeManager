"""
Self-Consistency Concept Extraction.

Research motivation
-------------------
Standard LLM extraction is stochastic: a single call may hallucinate a concept
or miss one depending on the exact token sample. Self-consistency [Wang et al.,
2023] runs the same prompt N times with slightly varied temperature and takes the
MAJORITY VOTE across runs. Applied to structured KG extraction this reduces both
false positives (concepts claimed but not present) and false negatives (concepts
missed).

Algorithm
---------
1. Run ConceptExtractor.extract() N times (default 3) with temperatures
   drawn from a small range [0.0, 0.15, 0.25].
2. A concept is accepted if it appears in >= k out of N runs (default k = 2).
3. Concept confidence is the MEAN confidence across the runs in which it appeared.
4. Relationships are accepted if both their endpoint concepts passed the vote.
5. overall_depth is the MAJORITY label across runs.

Effect on downstream scoring
-----------------------------
Fewer false-positive concepts → more accurate coverage score → higher grade
correlation. Fewer false-negative concepts → student is not penalised for
concepts the single-run LLM missed.
"""

from __future__ import annotations

import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from concept_extraction.extractor import ConceptExtractor, StudentConceptGraph, ExtractedConcept, ExtractedRelationship
    from knowledge_graph.domain_graph import DomainKnowledgeGraph
except ImportError:
    from extractor import ConceptExtractor, StudentConceptGraph, ExtractedConcept, ExtractedRelationship
    from knowledge_graph.domain_graph import DomainKnowledgeGraph


class SelfConsistentExtractor:
    """
    Wraps ConceptExtractor with majority-voting across N extraction runs.

    Parameters
    ----------
    domain_graph : DomainKnowledgeGraph
    api_key      : Groq API key
    model        : LLM model name
    n_runs       : Number of independent extraction runs (default 3)
    min_votes    : Minimum runs a concept must appear in to be accepted (default 2)
    temperatures : Temperature per run; length must equal n_runs
    """

    DEFAULT_TEMPERATURES = [0.0, 0.15, 0.25]

    def __init__(
        self,
        domain_graph: DomainKnowledgeGraph,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        n_runs: int = 3,
        min_votes: int = 2,
        temperatures: list[float] | None = None,
        inter_run_delay: float = 0.0,
    ):
        self.n_runs = n_runs
        self.min_votes = min_votes
        self.temperatures = temperatures or self.DEFAULT_TEMPERATURES[:n_runs]
        self.inter_run_delay = inter_run_delay
        if len(self.temperatures) != n_runs:
            raise ValueError(
                f"len(temperatures) ({len(self.temperatures)}) must equal n_runs ({n_runs})"
            )

        # One extractor per temperature (Groq client is thread-safe)
        self._extractors = [
            _TempExtractor(domain_graph, api_key, model, t)
            for t in self.temperatures
        ]

    # ── public API ──────────────────────────────────────────────────────────

    def extract(self, question: str, student_answer: str) -> StudentConceptGraph:
        """
        Extract with self-consistency voting.

        Returns a StudentConceptGraph whose concepts have passed a majority
        vote across n_runs independent LLM calls.

        All runs fire concurrently via ThreadPoolExecutor — modern APIs
        (Gemini, Claude, OpenAI) are concurrent-safe. inter_run_delay
        defaults to 0 and is kept only as an escape hatch for strict
        rate-limited endpoints.
        """
        runs: list[StudentConceptGraph] = [None] * self.n_runs  # type: ignore

        def _run(idx: int) -> tuple[int, StudentConceptGraph]:
            return idx, self._extractors[idx].extract(question, student_answer)

        with ThreadPoolExecutor(max_workers=self.n_runs) as pool:
            futures = {pool.submit(_run, i): i for i in range(self.n_runs)}
            for future in as_completed(futures):
                idx, graph = future.result()
                runs[idx] = graph

        return self._vote(question, student_answer, runs)

    # ── voting logic ────────────────────────────────────────────────────────

    def _vote(
        self,
        question: str,
        answer: str,
        runs: list[StudentConceptGraph],
    ) -> StudentConceptGraph:
        """Merge N graphs by majority vote."""

        # ── Concept voting ─────────────────────────────────────────────────
        # Track: concept_id → list of (confidence, is_correct_usage, evidence)
        concept_votes: dict[str, list] = {}
        for g in runs:
            for c in g.concepts:
                concept_votes.setdefault(c.concept_id, []).append(
                    (c.confidence, c.is_correct_usage, c.evidence)
                )

        accepted_concepts: list[ExtractedConcept] = []
        for cid, votes in concept_votes.items():
            if len(votes) >= self.min_votes:
                mean_conf = sum(v[0] for v in votes) / len(votes)
                # is_correct_usage: True if majority of votes say True
                is_correct = sum(1 for v in votes if v[1]) > len(votes) / 2
                best_evidence = max(votes, key=lambda v: v[0])[2]
                accepted_concepts.append(ExtractedConcept(
                    concept_id=cid,
                    confidence=round(mean_conf, 4),
                    evidence=best_evidence,
                    is_correct_usage=is_correct,
                ))

        accepted_ids = {c.concept_id for c in accepted_concepts}

        # ── Relationship voting ────────────────────────────────────────────
        rel_votes: dict[tuple, list] = {}
        for g in runs:
            for r in g.relationships:
                if r.source_id in accepted_ids and r.target_id in accepted_ids:
                    key = (r.source_id, r.target_id, r.relation_type)
                    rel_votes.setdefault(key, []).append(
                        (r.confidence, r.is_correct, r.evidence, r.misconception_note)
                    )

        accepted_rels: list[ExtractedRelationship] = []
        for (src, tgt, rtype), votes in rel_votes.items():
            if len(votes) >= self.min_votes:
                mean_conf = sum(v[0] for v in votes) / len(votes)
                is_correct = sum(1 for v in votes if v[1]) > len(votes) / 2
                best_evidence = max(votes, key=lambda v: v[0])[2]
                misc_note = next((v[3] for v in votes if v[3]), "")
                accepted_rels.append(ExtractedRelationship(
                    source_id=src,
                    target_id=tgt,
                    relation_type=rtype,
                    confidence=round(mean_conf, 4),
                    evidence=best_evidence,
                    is_correct=is_correct,
                    misconception_note=misc_note,
                ))

        # ── Unmapped terms (union across runs) ────────────────────────────
        all_unmapped = list({t for g in runs for t in g.unmapped_terms})

        # ── Depth (majority vote) ──────────────────────────────────────────
        depth_votes = Counter(g.overall_depth for g in runs)
        majority_depth = depth_votes.most_common(1)[0][0]

        merged = StudentConceptGraph(
            question=question,
            student_answer=answer,
            overall_depth=majority_depth,
        )
        merged.concepts = accepted_concepts
        merged.relationships = accepted_rels
        merged.unmapped_terms = all_unmapped

        print(
            f"  [SC] runs={self.n_runs}, voted concepts: "
            f"{sum(len(g.concepts) for g in runs)//self.n_runs:.0f} avg → "
            f"{len(accepted_concepts)} accepted "
            f"(min_votes={self.min_votes}/{self.n_runs})"
        )
        return merged


class _TempExtractor(ConceptExtractor):
    """ConceptExtractor with a fixed temperature override."""

    def __init__(
        self,
        domain_graph: DomainKnowledgeGraph,
        api_key: str,
        model: str,
        temperature: float,
    ):
        super().__init__(domain_graph=domain_graph, api_key=api_key, model=model)
        self._temperature = temperature

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=self._temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
