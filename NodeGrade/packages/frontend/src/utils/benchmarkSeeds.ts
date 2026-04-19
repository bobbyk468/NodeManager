/**
 * benchmarkSeeds.ts — Frontend mirror of data/benchmark_seeds.json
 *
 * Maps student_answer_id → pedagogical trap type for the ConceptGrade
 * Co-Auditing Benchmark (VIS 2027 user study, N=30, 15 per condition).
 *
 * Used at logging time in StudentAnswerPanel to inject a `benchmark_case`
 * field into answer_view_start / answer_view_end payloads whenever a
 * participant naturally navigates to a seeded answer via the Concept Heatmap.
 *
 * No UI is shown to participants — seeding is invisible and preserves the
 * ecological validity of the foraging task. The flag surfaces only in JSONL
 * logs, which the researcher reads post-study to measure:
 *   - Did Condition B catch the fluent_hallucination trace gap?
 *   - Did Condition B override the unorthodox_genius low score?
 *   - Did Condition B dwell longer on the lexical_bluffer?
 *   - What was the time-to-insight for the partial_credit_needle?
 *
 * Sync this file with packages/concept-aware/data/benchmark_seeds.json
 * whenever seeds change.
 */

export type BenchmarkCase =
  | 'fluent_hallucination'    // structural leap in LRM trace; score looks fine
  | 'unorthodox_genius'       // correct answer, colloquial vocab → low AI score
  | 'lexical_bluffer'         // keyword-stuffed; AI overestimates; CONTRADICTS buried
  | 'partial_credit_needle';  // balanced trace; missing concept only via KG subgraph

/**
 * BENCHMARK_SEEDS: student_answer_id (as string) → trap type.
 *
 * All IDs are from the DigiKlausur Neural Networks dataset.
 * Selected criteria:
 *   fluent_hallucination  — topological_gap_count ≥ 1 (only 2 exist in 300 answers)
 *   unorthodox_genius     — net_delta < -1.5, human_score ≥ 4.0
 *   lexical_bluffer       — net_delta > 0.8, contradicts_steps ≥ 2
 *   partial_credit_needle — human_score = 2.5, balanced SUPPORTS/CONTRADICTS
 */
const BENCHMARK_SEEDS: Readonly<Record<string, BenchmarkCase>> = {
  // fluent_hallucination
  '0':   'fluent_hallucination',   // gap=3, grounding=0.35, human=5.0, c5=5.0
  '9':   'fluent_hallucination',   // gap=1, grounding=0.35, human=5.0, c5=4.0
  // unorthodox_genius
  '276': 'unorthodox_genius',      // human=5.0, c5=1.0 (Δ = -2.35 — most extreme)
  '269': 'unorthodox_genius',      // human=5.0, c5=3.0 (Δ = -2.30)
  // lexical_bluffer
  '484': 'lexical_bluffer',        // human=2.5, c5=5.0 (Δ = +1.10, 2 CONTRADICTS)
  '505': 'lexical_bluffer',        // human=2.5, c5=3.0 (Δ = +0.80, 4 CONTRADICTS)
  // partial_credit_needle
  '32':  'partial_credit_needle',  // human=2.5, c5=2.0 (9 SUPPORTS, 7 CONTRADICTS)
  '558': 'partial_credit_needle',  // human=2.5, c5=2.5 (7 SUPPORTS, 7 CONTRADICTS)
} as const;

/**
 * Returns the benchmark trap type for a given student_answer_id,
 * or `undefined` if the answer is not a seeded benchmark case.
 *
 * @example
 *   getBenchmarkCase('276') // → 'unorthodox_genius'
 *   getBenchmarkCase('999') // → undefined
 */
export function getBenchmarkCase(
  studentAnswerId: string | number,
): BenchmarkCase | undefined {
  return BENCHMARK_SEEDS[String(studentAnswerId)];
}

/** Returns all seeded IDs as a Set<string> for fast membership tests. */
export const SEEDED_IDS = new Set(Object.keys(BENCHMARK_SEEDS));
