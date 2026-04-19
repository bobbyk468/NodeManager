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
  matched: boolean;        // did this student cover the selected concept?
  severity: 'critical' | 'moderate' | 'minor' | 'matched';
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

// ── KG subgraph (ego-graph around one concept) ────────────────────────────────

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

// ── Per-sample XAI data (for score provenance causal text) ───────────────────

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
  missing_concepts: string[];   // expected but not matched
}

// ── LRM Trace (Stage 3b output, served per answer) ────────────────────────────

export interface ParsedTraceStep {
  step_id: number;
  text: string;
  classification: 'SUPPORTS' | 'CONTRADICTS' | 'UNCERTAIN';
  kg_nodes: string[];
  kg_edges: string[];
  confidence_delta: number;
  is_conclusion: boolean;
}

export interface TraceSummary {
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
  lrm_valid: boolean;
  lrm_reasoning: string;
  lrm_model: string;
  lrm_latency_ms: number;
  parsed_steps: ParsedTraceStep[];
  trace_summary: TraceSummary;
}
