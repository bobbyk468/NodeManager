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
