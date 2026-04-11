import { Injectable, NotFoundException } from '@nestjs/common';
import * as fs from 'fs';
import * as path from 'path';
import {
  DatasetSummaryResponse,
  DatasetMetrics,
  VisualizationSpec,
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
  async listDatasets(): Promise<string[]> {
    if (!fs.existsSync(DATA_DIR)) {
      return [];
    }
    return fs
      .readdirSync(DATA_DIR)
      .filter((f) => f.endsWith('_eval_results.json'))
      .filter((f) => this.isPerSampleEvalFile(path.join(DATA_DIR, f)))
      .map((f) => f.replace('_eval_results.json', ''));
  }

  /** Skip ablation-style JSON (e.g. offline_eval_results.json) with no per-sample scores. */
  private isPerSampleEvalFile(filePath: string): boolean {
    try {
      const raw = JSON.parse(fs.readFileSync(filePath, 'utf8')) as EvalResults;
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
    const filePath = path.join(DATA_DIR, `${dataset}_eval_results.json`);
    if (!fs.existsSync(filePath)) {
      throw new NotFoundException(`Dataset '${dataset}' not found`);
    }
    const raw: EvalResults = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    return this.buildResponse(dataset, raw);
  }

  async getAllDatasets(): Promise<DatasetSummaryResponse[]> {
    const datasets = await this.listDatasets();
    return Promise.all(datasets.map((d) => this.getDatasetVisualization(d)));
  }

  private buildResponse(dataset: string, raw: EvalResults): DatasetSummaryResponse {
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

    const visualizations = this.adaptToVisualizationSpecs(
      results,
      n,
      metrics,
      wilcoxon_p,
      mae_reduction_pct,
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
  ): VisualizationSpec[] {
    return [
      this.buildClassSummary(results, n, metrics, wilcoxon_p, mae_reduction_pct),
      this.buildBloomsDist(results),
      this.buildSoloDist(results),
      this.buildScoreComparison(results),
      this.buildConceptFrequency(results),
      this.buildChainCoverageDist(results),
      this.buildScoreScatter(results),
      this.buildStudentRadarPlaceholder(),
      this.buildMisconceptionHeatmapPlaceholder(),
    ];
  }

  private buildStudentRadarPlaceholder(): VisualizationSpec {
    return {
      viz_id: 'student_radar',
      viz_type: 'radar',
      title: 'Student Coverage Radar',
      subtitle: 'Per-student concept mastery (extended pipeline only)',
      data: { dimensions: [], students: [] },
      config: {},
      insights: [
        'Requires per-student concept vectors from a full ConceptGrade export; cached batch eval JSON does not include this field.',
      ],
    };
  }

  private buildMisconceptionHeatmapPlaceholder(): VisualizationSpec {
    return {
      viz_id: 'misconception_heatmap',
      viz_type: 'heatmap',
      title: 'Misconception Severity Heatmap',
      subtitle: 'Concept × severity counts (extended pipeline only)',
      data: { cells: [], x_labels: ['critical', 'moderate', 'minor'], y_labels: [] },
      config: {},
      insights: [
        'Requires per-concept misconception counts from the grading pipeline; standard *_eval_results.json files omit this structure.',
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
        total_misconceptions: 0,
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
