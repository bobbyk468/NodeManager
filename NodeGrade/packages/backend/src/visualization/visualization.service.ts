import { Injectable, InternalServerErrorException, NotFoundException } from '@nestjs/common';
import { existsSync } from 'fs';
import { readFile, readdir, stat } from 'fs/promises';
import * as path from 'path';
import {
  DatasetSummaryResponse,
  DatasetMetrics,
  VisualizationSpec,
  ConceptAnswersResponse,
  ConceptStudentAnswer,
  KGSubgraphResponse,
  KGNode,
  KGEdge,
  SampleXAIData,
  SampleTraceResponse,
} from './visualization.types';

// Resolve concept-aware/data/ relative to compiled output:
// __dirname = packages/backend/dist/src/visualization → four levels up = packages/
const DATA_DIR = path.resolve(__dirname, '../../../../concept-aware/data');

// Bloom's taxonomy level mapping
const BLOOM_LEVEL_MAP: Record<string, number> = {
  Remember: 1,
  Understand: 2,
  Apply: 3,
  Analyze: 4,
  Evaluate: 5,
  Create: 6,
};

// SOLO taxonomy level mapping
const SOLO_LEVEL_MAP: Record<string, number> = {
  Prestructural: 1,
  Unistructural: 2,
  Multistructural: 3,
  Relational: 4,
  'Extended Abstract': 5,
};

// Color palettes matching visualization/renderer.py
const BLOOM_COLORS: Record<string, string> = {
  Remember: '#ef4444',
  Understand: '#f97316',
  Apply: '#eab308',
  Analyze: '#22c55e',
  Evaluate: '#3b82f6',
  Create: '#8b5cf6',
};

const SOLO_COLORS: Record<string, string> = {
  Prestructural: '#ef4444',
  Unistructural: '#f97316',
  Multistructural: '#eab308',
  Relational: '#22c55e',
  'Extended Abstract': '#3b82f6',
};

interface EvalSample {
  id: string | number;
  human_score: number;
  cllm_score: number;
  c5_score: number;
  matched_concepts?: string[];
  chain_pct?: string;
  solo?: string;
  bloom?: string;
}

interface EvalResults {
  dataset?: string;
  n?: number;
  results?: EvalSample[];
  metrics?: {
    C_LLM?: Partial<DatasetMetrics>;
    C5_fix?: Partial<DatasetMetrics>;
  };
  wilcoxon_p?: number;
  mae_reduction_pct?: number;
  [key: string]: unknown;
}

@Injectable()
export class VisualizationService {
  /** In-memory cache keyed by absolute file path. Each entry stores the parsed data
   *  and the file mtime (ms) at the time it was cached. On each access, a stat() call
   *  checks whether the file has been updated; if so, the cache entry is invalidated
   *  and the file is re-read. This handles the case where a researcher re-runs
   *  run_batch_eval_api.py while the server is still running. */
  private readonly fileCache = new Map<string, { data: unknown; mtimeMs: number }>();

  /** Async file read with mtime-aware caching.
   *  stat() is wrapped in try/catch: if the file is removed between existsSync()
   *  and stat() (TOCTOU race), the cached copy is served if available; otherwise
   *  a NotFoundException is thrown rather than an unhandled rejection. */
  private async loadJson<T>(filePath: string): Promise<T> {
    let currentMtime: number;
    try {
      currentMtime = (await stat(filePath)).mtimeMs;
    } catch {
      const cached = this.fileCache.get(filePath);
      if (cached) return cached.data as T;
      throw new NotFoundException(`File not found or removed: ${path.basename(filePath)}`);
    }

    const cached = this.fileCache.get(filePath);
    if (cached && cached.mtimeMs === currentMtime) {
      return cached.data as T;
    }

    const raw = await readFile(filePath, 'utf8');
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch (e) {
      throw new InternalServerErrorException(
        `Malformed JSON in eval results file '${path.basename(filePath)}': ${(e as Error).message}. ` +
        `Re-run run_batch_eval_api.py --dataset <name> to regenerate.`,
      );
    }
    this.fileCache.set(filePath, { data: parsed, mtimeMs: currentMtime });
    return parsed as T;
  }

  async listDatasets(): Promise<string[]> {
    try {
      const files = await readdir(DATA_DIR);
      const filtered = files.filter((f) => f.endsWith('_eval_results.json'));
      const checks = await Promise.all(
        filtered.map(async (f) => {
          const ok = await this.isPerSampleEvalFile(path.join(DATA_DIR, f));
          return ok ? f.replace('_eval_results.json', '') : null;
        }),
      );
      return checks.filter((x): x is string => x !== null);
    } catch (e) {
      const err = e as NodeJS.ErrnoException;
      if (err.code === 'ENOENT') return [];
      throw new InternalServerErrorException(`Cannot read dataset directory '${DATA_DIR}': ${err.message}`);
    }
  }

  /** Skip ablation-style JSON (e.g. offline_eval_results.json) with no per-sample scores. */
  private async isPerSampleEvalFile(filePath: string): Promise<boolean> {
    try {
      const raw = await this.loadJson<EvalResults>(filePath);
      const results = raw.results;
      if (!Array.isArray(results) || results.length === 0) {
        return false;
      }
      const s0 = results[0];
      return (
        typeof s0.human_score === 'number' &&
        typeof s0.cllm_score === 'number' &&
        typeof s0.c5_score === 'number'
      );
    } catch {
      return false;
    }
  }

  async getDatasetVisualization(dataset: string): Promise<DatasetSummaryResponse> {
    const safeDataset = path.basename(dataset);
    const filePath = path.join(DATA_DIR, `${safeDataset}_eval_results.json`);
    if (!existsSync(filePath)) {
      throw new NotFoundException(`Dataset '${safeDataset}' not found`);
    }
    const raw = await this.loadJson<EvalResults>(filePath);
    return this.buildResponse(safeDataset, raw);
  }

  async getAllDatasets(): Promise<DatasetSummaryResponse[]> {
    const datasets = await this.listDatasets();
    return Promise.all(datasets.map((d) => this.getDatasetVisualization(d)));
  }

  private async buildResponse(dataset: string, raw: EvalResults): Promise<DatasetSummaryResponse> {
    const results: EvalSample[] = raw.results ?? [];
    const n = raw.n ?? results.length;

    const metricsRaw = raw.metrics ?? {};
    const metrics = {
      C_LLM: this.coerceMetrics(metricsRaw.C_LLM),
      C5_fix: this.coerceMetrics(metricsRaw.C5_fix),
    };

    const wilcoxon_p = raw.wilcoxon_p ?? 1.0;
    const mae_reduction_pct = raw.mae_reduction_pct ??
      (metrics.C_LLM.mae > 0
        ? ((metrics.C_LLM.mae - metrics.C5_fix.mae) / metrics.C_LLM.mae) * 100
        : 0);

    // Load dashboard extras (student_radar + misconception_heatmap) if available.
    // Generated by: python3 generate_dashboard_extras.py
    const extrasPath = path.join(DATA_DIR, `${dataset}_dashboard_extras.json`);
    let extras: Record<string, unknown> | null = null;
    if (existsSync(extrasPath)) {
      try {
        extras = await this.loadJson<Record<string, unknown>>(extrasPath);
      } catch {
        extras = null;
      }
    }

    const visualizations = this.adaptToVisualizationSpecs(
      results,
      n,
      metrics,
      wilcoxon_p,
      mae_reduction_pct,
      extras,
    );

    return { dataset, n, metrics, wilcoxon_p, mae_reduction_pct, visualizations };
  }

  private coerceMetrics(raw?: Partial<DatasetMetrics>): DatasetMetrics {
    return {
      mae: raw?.mae ?? 0,
      rmse: raw?.rmse ?? 0,
      r: raw?.r ?? 0,
      rho: raw?.rho ?? 0,
      qwk: raw?.qwk ?? 0,
      bias: raw?.bias ?? 0,
    };
  }

  private adaptToVisualizationSpecs(
    results: EvalSample[],
    n: number,
    metrics: { C_LLM: DatasetMetrics; C5_fix: DatasetMetrics },
    wilcoxon_p: number,
    mae_reduction_pct: number,
    extras: Record<string, unknown> | null = null,
  ): VisualizationSpec[] {
    return [
      this.buildClassSummary(results, n, metrics, wilcoxon_p, mae_reduction_pct),
      this.buildBloomsDist(results),
      this.buildSoloDist(results),
      this.buildScoreComparison(results),
      this.buildConceptFrequency(results),
      this.buildChainCoverageDist(results),
      this.buildScoreScatter(results),
      this.buildStudentRadar(extras),
      this.buildMisconceptionHeatmap(extras),
    ];
  }

  private buildStudentRadar(extras: Record<string, unknown> | null): VisualizationSpec {
    const radarData = extras?.student_radar as Record<string, unknown> | undefined;
    const hasData =
      radarData &&
      Array.isArray(radarData.students) &&
      (radarData.students as unknown[]).length > 0;

    if (hasData) {
      const students = radarData!.students as Array<Record<string, unknown>>;
      const insights = [
        `${students.length} score quartile groups visualised across 5 cognitive dimensions.`,
      ];
      // Highlight the quartile gap on concept coverage (dim 0)
      if (students.length >= 2) {
        const low = (students[0].values as number[])[0];
        const high = (students[students.length - 1].values as number[])[0];
        insights.push(
          `Concept coverage gap: ${Math.round(low * 100)}% (Q1) → ${Math.round(high * 100)}% (Q4).`,
        );
      }
      return {
        viz_id: 'student_radar',
        viz_type: 'radar',
        title: 'Student Quartile Coverage Radar',
        subtitle: 'Cognitive profile by score quartile (Q1–Q4)',
        data: radarData as Record<string, unknown>,
        config: { max_value: 1.0 },
        insights,
      };
    }

    // Fallback placeholder
    return {
      viz_id: 'student_radar',
      viz_type: 'radar',
      title: 'Student Coverage Radar',
      subtitle: 'Per-student concept mastery',
      data: { dimensions: [], students: [] },
      config: {},
      insights: [
        'Run: python3 generate_dashboard_extras.py to populate this chart.',
      ],
    };
  }

  private buildMisconceptionHeatmap(extras: Record<string, unknown> | null): VisualizationSpec {
    const heatData = extras?.misconception_heatmap as Record<string, unknown> | undefined;
    const hasData =
      heatData &&
      Array.isArray(heatData.cells) &&
      (heatData.cells as unknown[]).length > 0;

    if (hasData) {
      const extInsights = Array.isArray(heatData!.insights) ? (heatData!.insights as string[]) : [];
      return {
        viz_id: 'misconception_heatmap',
        viz_type: 'heatmap',
        title: 'Misconception Severity Heatmap',
        subtitle: 'Concepts most often missed × student score level',
        data: heatData as Record<string, unknown>,
        config: { color_scale: ['#fef9c3', '#ef4444'] },
        insights: extInsights,
      };
    }

    // Fallback placeholder
    return {
      viz_id: 'misconception_heatmap',
      viz_type: 'heatmap',
      title: 'Misconception Severity Heatmap',
      subtitle: 'Concept × severity counts',
      data: { cells: [], x_labels: ['critical', 'moderate', 'minor'], y_labels: [] },
      config: {},
      insights: [
        'Run: python3 generate_dashboard_extras.py to populate this chart.',
      ],
    };
  }

  // Spec 1: class_summary (summary_card)
  private buildClassSummary(
    results: EvalSample[],
    n: number,
    metrics: { C_LLM: DatasetMetrics; C5_fix: DatasetMetrics },
    wilcoxon_p: number,
    mae_reduction_pct: number,
  ): VisualizationSpec {
    const avgC5 = results.length
      ? results.reduce((s, r) => s + r.c5_score, 0) / results.length
      : 0;
    const bloomLevels = results
      .map((r) => BLOOM_LEVEL_MAP[r.bloom ?? ''] ?? 0)
      .filter(Boolean);
    const soloLevels = results
      .map((r) => SOLO_LEVEL_MAP[r.solo ?? ''] ?? 0)
      .filter(Boolean);
    const avgBloom = bloomLevels.length
      ? bloomLevels.reduce((a, b) => a + b, 0) / bloomLevels.length
      : 0;
    const avgSolo = soloLevels.length
      ? soloLevels.reduce((a, b) => a + b, 0) / soloLevels.length
      : 0;

    const insights: string[] = [];
    if (mae_reduction_pct > 20) {
      insights.push(`Strong KG benefit: ${mae_reduction_pct.toFixed(1)}% MAE reduction over LLM baseline.`);
    } else if (mae_reduction_pct > 0) {
      insights.push(`Modest KG benefit: ${mae_reduction_pct.toFixed(1)}% MAE reduction. Domain vocabulary may limit matching signal.`);
    }
    if (wilcoxon_p < 0.05) {
      insights.push(`Improvement is statistically significant (Wilcoxon p = ${wilcoxon_p.toFixed(4)}).`);
    }

    return {
      viz_id: 'class_summary',
      viz_type: 'summary_card',
      title: 'Class Overview',
      subtitle: 'Aggregate grading statistics',
      data: {
        num_students: n,
        avg_score: avgC5,
        blooms_avg: avgBloom,
        solo_avg: avgSolo,
        total_misconceptions: results.filter((r) => (r.matched_concepts ?? []).length === 0).length,
        c_llm_mae: metrics.C_LLM.mae,
        c5_mae: metrics.C5_fix.mae,
        mae_reduction_pct,
        wilcoxon_p,
      },
      config: {},
      insights,
    };
  }

  // Spec 2: blooms_dist (bar_chart)
  private buildBloomsDist(results: EvalSample[]): VisualizationSpec {
    const counts: Record<string, number> = {};
    for (const r of results) {
      if (r.bloom) counts[r.bloom] = (counts[r.bloom] ?? 0) + 1;
    }
    const total = results.length || 1;
    const order = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'];
    const bars = order
      .filter((l) => counts[l] !== undefined)
      .map((label) => ({
        label,
        level: BLOOM_LEVEL_MAP[label] ?? 0,
        count: counts[label] ?? 0,
        percentage: Math.round(((counts[label] ?? 0) / total) * 100),
        color: BLOOM_COLORS[label] ?? '#64748b',
      }));

    const topLevel = bars.reduce((a, b) => (a.count > b.count ? a : b), bars[0]);
    const insights = topLevel
      ? [`Most common Bloom's level: ${topLevel.label} (${topLevel.percentage}% of students).`]
      : [];

    return {
      viz_id: 'blooms_dist',
      viz_type: 'bar_chart',
      title: "Bloom's Taxonomy Distribution",
      subtitle: 'Cognitive level of student responses',
      data: { bars, x_label: "Bloom's Level", y_label: 'Students' },
      config: { orientation: 'vertical', show_percentages: true },
      insights,
    };
  }

  // Spec 3: solo_dist (bar_chart)
  private buildSoloDist(results: EvalSample[]): VisualizationSpec {
    const counts: Record<string, number> = {};
    for (const r of results) {
      if (r.solo) counts[r.solo] = (counts[r.solo] ?? 0) + 1;
    }
    const total = results.length || 1;
    const order = ['Prestructural', 'Unistructural', 'Multistructural', 'Relational', 'Extended Abstract'];
    const bars = order
      .filter((l) => counts[l] !== undefined)
      .map((label) => ({
        label,
        level: SOLO_LEVEL_MAP[label] ?? 0,
        count: counts[label] ?? 0,
        percentage: Math.round(((counts[label] ?? 0) / total) * 100),
        color: SOLO_COLORS[label] ?? '#64748b',
      }));

    const deepCount = (counts['Relational'] ?? 0) + (counts['Extended Abstract'] ?? 0);
    const deepPct = Math.round((deepCount / total) * 100);
    const insights = [`${deepPct}% of students show deep structural understanding (Relational or Extended Abstract).`];

    return {
      viz_id: 'solo_dist',
      viz_type: 'bar_chart',
      title: 'SOLO Taxonomy Distribution',
      subtitle: 'Structural complexity of student responses',
      data: { bars, x_label: 'SOLO Level', y_label: 'Students' },
      config: { orientation: 'vertical', show_percentages: true },
      insights,
    };
  }

  // Spec 4: score_comparison (grouped_bar) — MAE per score bucket
  private buildScoreComparison(results: EvalSample[]): VisualizationSpec {
    const buckets = ['0–1', '1–2', '2–3', '3–4', '4–5'];
    const bucketData = buckets.map((label, i) => {
      const inBucket = results.filter(
        (r) => r.human_score >= i && r.human_score < i + 1,
      );
      const cllmMae = inBucket.length
        ? inBucket.reduce((s, r) => s + Math.abs(r.human_score - r.cllm_score), 0) /
          inBucket.length
        : 0;
      const c5Mae = inBucket.length
        ? inBucket.reduce((s, r) => s + Math.abs(r.human_score - r.c5_score), 0) /
          inBucket.length
        : 0;
      return {
        student_id: label,
        cllm_mae: Math.round(cllmMae * 1000) / 1000,
        c5_mae: Math.round(c5Mae * 1000) / 1000,
        count: inBucket.length,
      };
    });

    const insights = [
      'Each bar group shows Mean Absolute Error (MAE) within each human score range.',
      'Lower is better. ConceptGrade (orange) should track below LLM baseline (blue) in technical domains.',
    ];

    return {
      viz_id: 'score_comparison',
      viz_type: 'grouped_bar',
      title: 'Score Comparison by Range',
      subtitle: 'MAE of LLM baseline vs ConceptGrade per score bucket',
      data: {
        students: bucketData,
        metrics: ['cllm_mae', 'c5_mae'],
        labels: { cllm_mae: 'C_LLM MAE', c5_mae: 'ConceptGrade MAE' },
      },
      config: { show_values: true },
      insights,
    };
  }

  // Spec 5: concept_frequency (bar_chart) — top 15 matched concepts
  private buildConceptFrequency(results: EvalSample[]): VisualizationSpec {
    const freq: Record<string, number> = {};
    for (const r of results) {
      for (const c of r.matched_concepts ?? []) {
        freq[c] = (freq[c] ?? 0) + 1;
      }
    }
    const sorted = Object.entries(freq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15);
    const bars = sorted.map(([concept, count]) => ({
      label: concept.replace(/_/g, ' '),
      concept,
      count,
      percentage: Math.round((count / (results.length || 1)) * 100),
      color: '#3b82f6',
    }));

    const insights =
      bars.length > 0
        ? [
            `Most covered concept: "${bars[0].label}" (${bars[0].percentage}% of students).`,
            bars.length >= 15
              ? 'Showing top 15 concepts by coverage frequency.'
              : `${bars.length} unique concepts covered across all students.`,
          ]
        : ['No concept match data available for this dataset.'];

    return {
      viz_id: 'concept_frequency',
      viz_type: 'bar_chart',
      title: 'Top Covered Concepts',
      subtitle: 'How often each expected concept appears in student answers',
      data: { bars, x_label: 'Coverage Count', y_label: 'Concept' },
      config: { orientation: 'horizontal', show_percentages: true },
      insights,
    };
  }

  // Spec 6: chain_coverage_dist (bar_chart) — distribution of KG chain coverage
  private buildChainCoverageDist(results: EvalSample[]): VisualizationSpec {
    const bucketLabels = ['0–20%', '20–40%', '40–60%', '60–80%', '80–100%'];
    const counts = [0, 0, 0, 0, 0];

    for (const r of results) {
      if (!r.chain_pct) continue;
      const pct = parseInt(String(r.chain_pct).replace('%', ''), 10);
      if (isNaN(pct)) continue;
      const bucket = Math.min(Math.floor(pct / 20), 4);
      counts[bucket]++;
    }

    const total = results.length || 1;
    const colors = ['#fca5a5', '#fdba74', '#fde68a', '#86efac', '#4ade80'];
    const bars = bucketLabels.map((label, i) => ({
      label,
      count: counts[i],
      percentage: Math.round((counts[i] / total) * 100),
      color: colors[i],
    }));

    const highCoverage = counts[3] + counts[4];
    const insights = [
      `${Math.round((highCoverage / total) * 100)}% of students covered 60%+ of the KG causal chain.`,
    ];

    return {
      viz_id: 'chain_coverage_dist',
      viz_type: 'bar_chart',
      title: 'KG Chain Coverage Distribution',
      subtitle: 'Fraction of expected concept chain each student addressed',
      data: { bars, x_label: 'Chain Coverage', y_label: 'Students' },
      config: { orientation: 'vertical', show_percentages: true },
      insights,
    };
  }

  // ── Linking & brushing: drill-down into one concept ─────────────────────────

  async getConceptStudentAnswers(
    dataset: string,
    conceptId: string,
  ): Promise<ConceptAnswersResponse> {
    const safeDataset = path.basename(dataset);
    const evalPath = path.join(DATA_DIR, `${safeDataset}_eval_results.json`);
    const datasetPath = path.join(DATA_DIR, `${safeDataset}_dataset.json`);
    const kgPath = path.join(DATA_DIR, `${safeDataset}_auto_kg.json`);

    if (!existsSync(evalPath)) {
      throw new NotFoundException(`Dataset '${safeDataset}' not found`);
    }

    const evalRaw = await this.loadJson<EvalResults>(evalPath);
    const results: EvalSample[] = evalRaw.results ?? [];

    // Load student answer text
    type DatasetRow = {
      id: string | number;
      question: string;
      reference_answer: string;
      student_answer: string;
      question_id?: string;
    };
    let datasetRows: DatasetRow[] = [];
    if (existsSync(datasetPath)) {
      datasetRows = await this.loadJson<DatasetRow[]>(datasetPath);
    }
    const rowById = new Map<string, DatasetRow>();
    for (const row of datasetRows) {
      rowById.set(String(row.id), row);
    }

    // Find which questions expect this concept (from KG)
    type KGRaw = {
      question_kgs?: Record<string, { expected_concepts?: string[] }>;
    };
    let questionIdsExpecting: Set<string | undefined> = new Set();
    let conceptName = conceptId.replace(/_/g, ' ');
    let conceptDescription = '';

    if (existsSync(kgPath)) {
      const kgRaw = await this.loadJson<KGRaw>(kgPath);
      const qKGs = kgRaw.question_kgs ?? {};
      for (const [, qdata] of Object.entries(qKGs)) {
        const expected = (qdata as Record<string, unknown>).expected_concepts as string[] ?? [];
        if (expected.includes(conceptId)) {
          const qId = (qdata as Record<string, unknown>).question_id as string | undefined;
          questionIdsExpecting.add(qId);
        }
        // Get concept definition
        const concepts = (qdata as Record<string, unknown>).concepts as Array<Record<string, string>> ?? [];
        for (const c of concepts) {
          if (c.id === conceptId) {
            conceptName = c.name ?? conceptName;
            conceptDescription = c.description ?? '';
          }
        }
      }
    }

    // Build per-student rows only for samples from questions that expect this concept.
    // When KG question_id data is available, filter missed cases to the relevant questions
    // so educators don't see students who were never asked about this concept.
    const qIdKnown = questionIdsExpecting.size > 0;
    const answers: ConceptStudentAnswer[] = [];
    for (const r of results) {
      const matched = (r.matched_concepts ?? []).includes(conceptId);
      const row = rowById.get(String(r.id));
      if (!row) continue;

      // When KG question_id data is available, restrict to questions that expect this concept.
      // Both matched and missed cases are filtered: an off-topic "match" is not meaningful
      // and would confuse educators browsing the concept drill-down.
      if (qIdKnown && !questionIdsExpecting.has(row.question_id)) continue;

      const severity: ConceptStudentAnswer['severity'] = matched
        ? 'matched'
        : r.human_score >= 3.5
        ? 'critical'
        : r.human_score >= 2.0
        ? 'moderate'
        : 'minor';

      answers.push({
        id: r.id,
        question: row.question,
        reference_answer: row.reference_answer,
        student_answer: row.student_answer,
        human_score: r.human_score,
        cllm_score: r.cllm_score,
        c5_score: r.c5_score,
        chain_pct: r.chain_pct ?? '',
        solo: r.solo ?? '',
        bloom: r.bloom ?? '',
        matched,
        severity,
      });
    }

    // Sort: matched first (green), then critical misses, then moderate, then minor
    const severityOrder = { matched: 0, critical: 1, moderate: 2, minor: 3 };
    answers.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

    const matched_count = answers.filter((a) => a.matched).length;
    const missed_count = answers.filter((a) => !a.matched).length;

    return {
      dataset,
      concept_id: conceptId,
      concept_name: conceptName,
      concept_description: conceptDescription,
      total: answers.length,
      matched_count,
      missed_count,
      answers,
    };
  }

  // ── KG subgraph: ego-graph around one concept ─────────────────────────────

  async getConceptKGSubgraph(
    dataset: string,
    conceptId: string,
    /** Optional: scope is_expected to the question the instructor is currently examining. */
    questionId?: string,
  ): Promise<KGSubgraphResponse> {
    const safeDataset = path.basename(dataset);
    const kgPath = path.join(DATA_DIR, `${safeDataset}_auto_kg.json`);
    if (!existsSync(kgPath)) {
      throw new NotFoundException(`KG data not found for dataset '${safeDataset}'`);
    }

    type RawConcept = { id: string; name: string; description: string };
    type RawRel = { from: string; to: string; type: string; weight: number; description: string };
    type QKG = { concepts?: RawConcept[]; relationships?: RawRel[]; expected_concepts?: string[] };
    type KGFile = { question_kgs?: Record<string, QKG> };

    const kgRaw = await this.loadJson<KGFile>(kgPath);
    const qKGs = kgRaw.question_kgs ?? {};

    // Collect all concepts and relationships mentioning this concept from any question
    const nodeMap = new Map<string, RawConcept>();
    const edgesRaw: RawRel[] = [];
    const expectedSet = new Set<string>();

    for (const [qId, qdata] of Object.entries(qKGs)) {
      const concepts: RawConcept[] = qdata.concepts ?? [];
      const rels: RawRel[] = qdata.relationships ?? [];
      const expected: string[] = qdata.expected_concepts ?? [];

      // Collect expected concepts — scoped to questionId if provided, global otherwise.
      // Scoping prevents false "missing" signals from unrelated questions.
      if (!questionId || qId === questionId) {
        for (const e of expected) expectedSet.add(e);
      }

      // Check if this question's KG involves our target concept
      const conceptIds = new Set(concepts.map((c) => c.id));
      if (!conceptIds.has(conceptId)) continue;

      // Index all concepts for this question
      for (const c of concepts) nodeMap.set(c.id, c);

      // Collect edges where our target concept is src or dst
      for (const rel of rels) {
        if (rel.from === conceptId || rel.to === conceptId) {
          edgesRaw.push(rel);
        }
      }
    }

    if (!nodeMap.has(conceptId)) {
      throw new NotFoundException(`Concept '${conceptId}' not found in KG for dataset '${dataset}'`);
    }

    // Build ego-graph: central node + 1-hop neighbors
    const neighborIds = new Set<string>();
    for (const e of edgesRaw) {
      if (e.from === conceptId) neighborIds.add(e.to);
      if (e.to === conceptId) neighborIds.add(e.from);
    }

    const nodes: KGNode[] = [];
    // Central node
    const central = nodeMap.get(conceptId)!;
    nodes.push({
      id: central.id,
      name: central.name,
      description: central.description,
      is_central: true,
      is_expected: expectedSet.has(central.id),
    });
    // Neighbor nodes
    for (const nid of neighborIds) {
      if (nid === conceptId) continue;
      const n = nodeMap.get(nid);
      if (!n) continue;
      nodes.push({
        id: n.id,
        name: n.name,
        description: n.description,
        is_central: false,
        is_expected: expectedSet.has(n.id),
      });
    }

    // De-duplicate edges — average the weight across occurrences (consensus strength).
    // First occurrence wins for description; weight is the mean over all instances.
    const edgeMap = new Map<string, { sum: number; count: number; e: RawRel }>();
    for (const e of edgesRaw) {
      const key = `${e.from}→${e.to}→${e.type}`;
      if (!edgeMap.has(key)) {
        edgeMap.set(key, { sum: 0, count: 0, e });
      }
      const entry = edgeMap.get(key)!;
      entry.sum += e.weight ?? 1;
      entry.count += 1;
    }
    const edges: KGEdge[] = Array.from(edgeMap.values()).map(({ sum, count, e }) => ({
      from: e.from,
      to: e.to,
      type: e.type,
      weight: sum / count,
      description: e.description ?? '',
    }));

    return { dataset, concept_id: conceptId, nodes, edges };
  }

  // ── Per-sample XAI: matched + expected + missing concepts ────────────────────

  async getSampleXAI(dataset: string, sampleId: string): Promise<SampleXAIData> {
    const safeDataset = path.basename(dataset);
    const evalPath    = path.join(DATA_DIR, `${safeDataset}_eval_results.json`);
    const datasetPath = path.join(DATA_DIR, `${safeDataset}_dataset.json`);
    const kgPath      = path.join(DATA_DIR, `${safeDataset}_auto_kg.json`);

    if (!existsSync(evalPath)) {
      throw new NotFoundException(`Dataset '${safeDataset}' not found`);
    }

    const evalRaw = await this.loadJson<EvalResults>(evalPath);
    const sample = (evalRaw.results ?? []).find((r) => String(r.id) === sampleId);
    if (!sample) throw new NotFoundException(`Sample '${sampleId}' not found`);

    // Load student answer text
    type DatasetRow = { id: string|number; question: string; reference_answer: string; student_answer: string; question_id?: string };
    let question = '', referenceAnswer = '', studentAnswer = '', questionId: string | undefined;
    if (existsSync(datasetPath)) {
      const rows = await this.loadJson<DatasetRow[]>(datasetPath);
      const row = rows.find((r) => String(r.id) === sampleId);
      if (row) {
        question        = row.question;
        referenceAnswer = row.reference_answer;
        studentAnswer   = row.student_answer;
        questionId      = row.question_id;
      }
    }

    // Get expected concepts from KG via question text matching
    const matchedConcepts: string[] = sample.matched_concepts ?? [];
    let expectedConcepts: string[] = [];

    if (existsSync(kgPath)) {
      type KGFile = { question_kgs?: Record<string, { question?: string; expected_concepts?: string[] }> };
      const kgRaw = await this.loadJson<KGFile>(kgPath);
      const qKGs  = kgRaw.question_kgs ?? {};

      // Match by question_id if available, else by normalized question text
      const qNorm = question.trim().toLowerCase();
      for (const qdata of Object.values(qKGs)) {
        const isMatch = questionId
          ? (qdata as Record<string,unknown>).question_id === questionId
          : (qdata.question ?? '').trim().toLowerCase() === qNorm;
        if (isMatch) {
          expectedConcepts = qdata.expected_concepts ?? [];
          break;
        }
      }
      // Fallback: match by question text prefix (first 60 chars)
      if (expectedConcepts.length === 0 && qNorm.length > 10) {
        for (const qdata of Object.values(qKGs)) {
          if ((qdata.question ?? '').trim().toLowerCase().startsWith(qNorm.slice(0, 60))) {
            expectedConcepts = qdata.expected_concepts ?? [];
            break;
          }
        }
      }
    }

    const matchedSet = new Set(matchedConcepts);
    const missingConcepts = expectedConcepts.filter((c) => !matchedSet.has(c));

    return {
      id:                sample.id,
      question,
      reference_answer:  referenceAnswer,
      student_answer:    studentAnswer,
      human_score:       sample.human_score,
      cllm_score:        sample.cllm_score,
      c5_score:          sample.c5_score,
      chain_pct:         sample.chain_pct ?? '',
      solo:              sample.solo ?? '',
      bloom:             sample.bloom ?? '',
      matched_concepts:  matchedConcepts,
      expected_concepts: expectedConcepts,
      missing_concepts:  missingConcepts,
    };
  }

  /**
   * GET /api/visualization/datasets/:dataset/sample/:sampleId/trace
   *
   * Serves the Stage 3b TraceParser output for a single answer.
   * Reads from {dataset}_lrm_traces.json — a file produced by the ablation
   * runner (run_lrm_ablation.py) which calls LRMVerifier + TraceParser in batch.
   *
   * Returns null (→ 204 in controller) if the trace file does not exist yet,
   * so the VerifierReasoningPanel can display a graceful empty state.
   */
  async getSampleTrace(
    dataset: string,
    sampleId: string,
  ): Promise<SampleTraceResponse | null> {
    const safeDataset = path.basename(dataset);
    const tracePath   = path.join(DATA_DIR, `${safeDataset}_lrm_traces.json`);

    if (!existsSync(tracePath)) return null;

    type TraceFile = Record<string, SampleTraceResponse>;
    const traceFile = await this.loadJson<TraceFile>(tracePath);
    return traceFile[sampleId] ?? null;
  }

  // Spec 7: score_scatter (table) — raw per-sample data
  private buildScoreScatter(results: EvalSample[]): VisualizationSpec {
    const rows = results.map((r) => ({
      id: r.id,
      human_score: r.human_score,
      cllm_score: r.cllm_score,
      c5_score: r.c5_score,
      cllm_error: Math.round(Math.abs(r.human_score - r.cllm_score) * 100) / 100,
      c5_error: Math.round(Math.abs(r.human_score - r.c5_score) * 100) / 100,
      solo: r.solo ?? '',
      bloom: r.bloom ?? '',
      chain_pct: r.chain_pct ?? '',
    }));

    return {
      viz_id: 'score_scatter',
      viz_type: 'table',
      title: 'Per-Sample Score Table',
      subtitle: 'Raw scores for all samples — useful for study analysis',
      data: {
        columns: [
          'id', 'human_score', 'cllm_score', 'c5_score',
          'cllm_error', 'c5_error', 'solo', 'bloom', 'chain_pct',
        ],
        rows,
      },
      config: { sortable: true, exportable: true },
      insights: [
        'cllm_error and c5_error show absolute deviation from human score.',
        'Sort by cllm_error descending to find cases where the LLM baseline fails most.',
      ],
    };
  }
}
