export type BenchmarkCase =
  | 'fluent_hallucination'
  | 'unorthodox_genius'
  | 'lexical_bluffer'
  | 'partial_credit_needle';

// Maps student_answer_id → trap type. Sync with data/benchmark_seeds.json.
const BENCHMARK_SEEDS: Readonly<Record<string, BenchmarkCase>> = {
  '0':   'fluent_hallucination',
  '9':   'fluent_hallucination',
  '276': 'unorthodox_genius',
  '269': 'unorthodox_genius',
  '484': 'lexical_bluffer',
  '505': 'lexical_bluffer',
  '32':  'partial_credit_needle',
  '558': 'partial_credit_needle',
} as const;

export function getBenchmarkCase(
  studentAnswerId: string | number,
): BenchmarkCase | undefined {
  return BENCHMARK_SEEDS[String(studentAnswerId)];
}

export const SEEDED_IDS = new Set(Object.keys(BENCHMARK_SEEDS));
