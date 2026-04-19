export type VizType =
  | 'bar_chart'
  | 'heatmap'
  | 'grouped_bar'
  | 'radar'
  | 'table'
  | 'summary_card'
  | 'concept_map';

export interface VisualizationSpec {
  viz_id: string;
  viz_type: VizType;
  title: string;
  subtitle: string;
  data: Record<string, unknown>;
  config: Record<string, unknown>;
  insights: string[];
}

export interface DatasetMetrics {
  mae: number;
  rmse: number;
  r: number;
  rho: number;
  qwk: number;
  bias: number;
}

export interface DatasetSummaryResponse {
  dataset: string;
  n: number;
  metrics: {
    C_LLM: DatasetMetrics;
    C5_fix: DatasetMetrics;
  };
  wilcoxon_p: number;
  mae_reduction_pct: number;
  visualizations: VisualizationSpec[];
}

// ── Concept drill-down (linking & brushing) ──────────────────────────────────

export type ConceptSeverity = 'matched' | 'critical' | 'moderate' | 'minor';

export interface ConceptStudentAnswer {
  id: string | number;
  question: string;
  reference_answer: string;
  student_answer: string;
  human_score: number;
  cllm_score: number;
  c5_score: number;
  chain_pct: string;
  solo: string;
  bloom: string;
  matched: boolean;
  severity: ConceptSeverity;
}

export interface ConceptAnswersResponse {
  dataset: string;
  concept_id: string;
  concept_name: string;
  concept_description: string;
  total: number;
  matched_count: number;
  missed_count: number;
  answers: ConceptStudentAnswer[];
}

// ── KG subgraph ──────────────────────────────────────────────────────────────

export interface KGNode {
  id: string;
  name: string;
  description: string;
  is_central: boolean;
  is_expected: boolean;
}

export interface KGEdge {
  from: string;
  to: string;
  type: string;
  weight: number;
  description: string;
}

export interface KGSubgraphResponse {
  dataset: string;
  concept_id: string;
  nodes: KGNode[];
  edges: KGEdge[];
}

// ── LRM trace (Stage 3a/3b) ───────────────────────────────────────────────────

export interface SampleTraceStep {
  step_id: number;
  text: string;
  classification: 'SUPPORTS' | 'CONTRADICTS' | 'UNCERTAIN';
  kg_nodes: string[];
  kg_edges: string[];
  confidence_delta: number;
  is_conclusion: boolean;
}

export interface SampleTraceSummary {
  total_steps: number;
  supports_count: number;
  contradicts_count: number;
  uncertain_count: number;
  net_delta: number;
  conclusion_text: string;
  nodes_referenced: string[];
  edges_referenced: string[];
}

export interface SampleTraceResponse {
  id: string | number;
  dataset: string;
  lrm_valid: boolean | null;
  lrm_reasoning: string;
  lrm_model: string;
  lrm_latency_ms: number;
  parsed_steps: SampleTraceStep[];
  trace_summary: SampleTraceSummary;
}

// ── Per-sample XAI data ───────────────────────────────────────────────────────

export interface SampleXAIData {
  id: string | number;
  question: string;
  reference_answer: string;
  student_answer: string;
  human_score: number;
  cllm_score: number;
  c5_score: number;
  chain_pct: string;
  solo: string;
  bloom: string;
  matched_concepts: string[];
  expected_concepts: string[];
  missing_concepts: string[];
}
