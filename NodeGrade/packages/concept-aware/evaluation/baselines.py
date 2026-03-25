"""
Baseline Comparators for ConceptGrade Evaluation.

Provides baseline scoring methods to benchmark ConceptGrade against:
  1. Cosine Similarity (TF-IDF) — classical NLP baseline
  2. LLM Zero-Shot Scoring — direct LLM grading without concept analysis

These baselines replicate approaches from Mohler et al. (2011) and
recent LLM-based ASAG systems for fair comparison.

References:
  - Mohler & Mihalcea (2009): Text similarity baselines (r=0.518)
  - Mohler et al. (2011): Dependency graph alignment (r=0.518)
  - Filighera et al. (2022): Transformer-based ASAG survey
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from conceptgrade.llm_client import LLMClient as Groq


@dataclass
class BaselineScore:
    """Score from a baseline method."""
    method: str
    raw_score: float       # 0.0 to 1.0
    scaled_score: float    # Scaled to target range (e.g., 0-5)
    metadata: dict = field(default_factory=dict)


class CosineSimilarityBaseline:
    """
    TF-IDF Cosine Similarity Baseline.

    Replicates the classical text similarity baseline from
    Mohler & Mihalcea (2009). Computes TF-IDF vectors for
    reference and student answers, then uses cosine similarity
    as the score.

    This is the simplest reasonable baseline — it captures
    lexical overlap but ignores semantics, structure, and depth.
    """

    def __init__(self, scale_max: float = 5.0):
        self.scale_max = scale_max
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )

    def score(
        self,
        reference_answer: str,
        student_answer: str,
    ) -> BaselineScore:
        """
        Score a single student answer against the reference.

        Delegates to score_batch for a consistent vocabulary — both texts are
        fitted together so TF-IDF weights are computed on the same vocabulary
        as the batch variant, making individual and batch scores comparable.
        """
        result = self.score_batch(reference_answer, [student_answer])
        return result[0]

    def score_batch(
        self,
        reference_answer: str,
        student_answers: list[str],
    ) -> list[BaselineScore]:
        """
        Score multiple student answers against the same reference.

        More efficient than individual scoring — fits TF-IDF once.
        """
        all_texts = [reference_answer] + student_answers

        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            ref_vec = tfidf_matrix[0:1]
            similarities = sklearn_cosine(ref_vec, tfidf_matrix[1:]).flatten()
        except Exception:
            similarities = np.zeros(len(student_answers))

        results = []
        for cos_sim in similarities:
            cos_sim = float(cos_sim)
            results.append(BaselineScore(
                method="cosine_similarity",
                raw_score=cos_sim,
                scaled_score=round(cos_sim * self.scale_max, 2),
                metadata={"similarity_type": "tfidf_cosine"},
            ))
        return results


class LLMZeroShotBaseline:
    """
    LLM Zero-Shot Scoring Baseline.

    Uses a large language model with a simple prompt to directly
    assign a grade (0-5) without any concept extraction, knowledge
    graph comparison, or cognitive depth analysis.

    This represents the "just throw it at an LLM" approach —
    the simplest possible LLM-based ASAG system.
    """

    SCORING_PROMPT = """You are an expert Computer Science educator grading student answers.

Grade the following student answer on a scale of 0 to 5 (integers only):
  0 = No understanding, completely wrong or irrelevant
  1 = Minimal understanding, only vaguely related
  2 = Basic understanding, mentions some relevant ideas but incomplete
  3 = Moderate understanding, covers main points but misses important details
  4 = Good understanding, covers most key concepts with minor gaps
  5 = Excellent understanding, comprehensive and accurate

QUESTION: {question}

REFERENCE ANSWER: {reference_answer}

STUDENT ANSWER: {student_answer}

Respond with ONLY a JSON object:
{{"score": <0-5>, "reasoning": "<brief 1-sentence explanation>"}}"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        scale_max: float = 5.0,
        rate_limit_delay: float = 1.5,
    ):
        self.api_key = api_key
        self.model = model
        self.scale_max = scale_max
        self.rate_limit_delay = rate_limit_delay
        self.client = Groq(api_key=api_key)

    def score(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
    ) -> BaselineScore:
        """
        Score a student answer using zero-shot LLM grading.

        Args:
            question: The assessment question
            reference_answer: Expert/model answer
            student_answer: Student's response

        Returns:
            BaselineScore with LLM-assigned grade
        """
        if not self.client:
            return BaselineScore(
                method="llm_zero_shot",
                raw_score=0.0,
                scaled_score=0.0,
                metadata={"error": "Groq client not available"},
            )

        prompt = self.SCORING_PROMPT.format(
            question=question,
            reference_answer=reference_answer,
            student_answer=student_answer,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise grading assistant. Respond only with JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON — handle markdown code blocks (Gemini wraps in ```json)
            # and nested braces (reasoning field may contain curly braces)
            parsed = None
            # 1. Strip markdown code fences
            md_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
            if md_match:
                try:
                    parsed = json.loads(md_match.group(1).strip())
                except json.JSONDecodeError:
                    pass
            # 2. Try raw JSON parse
            if parsed is None:
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    pass
            # 3. Find outermost { } pair
            if parsed is None:
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    try:
                        parsed = json.loads(content[start:end + 1])
                    except json.JSONDecodeError:
                        pass

            if parsed is not None:
                llm_score = int(round(float(parsed.get("score", 0))))
                reasoning = parsed.get("reasoning", "")
            else:
                # Last resort: extract any digit 0-5
                num_match = re.search(r'\b([0-5])\b', content)
                llm_score = int(num_match.group(1)) if num_match else 0
                reasoning = content

            llm_score = max(0, min(5, llm_score))
            raw = llm_score / self.scale_max

            return BaselineScore(
                method="llm_zero_shot",
                raw_score=raw,
                scaled_score=float(llm_score),
                metadata={
                    "model": self.model,
                    "reasoning": reasoning,
                },
            )

        except Exception as e:
            return BaselineScore(
                method="llm_zero_shot",
                raw_score=0.0,
                scaled_score=0.0,
                metadata={"error": str(e)},
            )

    def score_batch(
        self,
        question: str,
        reference_answer: str,
        student_answers: list[str],
    ) -> list[BaselineScore]:
        """
        Score multiple student answers using LLM zero-shot grading.

        Includes rate limiting between API calls.
        """
        results = []
        for answer in student_answers:
            result = self.score(question, reference_answer, answer)
            results.append(result)
            time.sleep(self.rate_limit_delay)
        return results
