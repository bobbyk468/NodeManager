import DownloadIcon from '@mui/icons-material/Download';
import RefreshIcon from '@mui/icons-material/Refresh';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  Divider,
  Grid,
  Slider,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import IconButton from '@mui/material/IconButton';
import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import {
  BloomsBarChart,
  ChainCoverageChart,
  ConceptFrequencyChart,
  MisconceptionHeatmap,
  ScoreComparisonChart,
  ScoreSamplesTable,
  SoloBarChart,
  StudentRadarChart,
} from '../components/charts';
import { DatasetSummaryResponse, VisualizationSpec } from '../common/visualization.types';
import {
  SESSION_ID,
  exportStudyLog,
  logEvent,
} from '../utils/studyLogger';

const DATASET_LABELS: Record<string, string> = {
  mohler: 'Mohler 2011 (CS)',
  offline: 'Mohler 2011 (CS)',
  digiklausur: 'DigiKlausur (NN)',
  kaggle_asag: 'Kaggle ASAG (Science)',
};

function getApiBase(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cfg = (window as any).__APP_CONFIG__ ?? {};
    return (cfg.API ?? 'http://localhost:5001/').replace(/\/$/, '');
  } catch {
    return 'http://localhost:5001';
  }
}

function findSpec(specs: VisualizationSpec[], vizId: string): VisualizationSpec | undefined {
  return specs.find((s) => s.viz_id === vizId);
}

function MetricCard({
  label,
  value,
  unit = '',
  color,
  tooltip,
}: {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
  tooltip?: string;
}) {
  return (
    <Tooltip title={tooltip ?? ''} arrow>
      <Card variant="outlined" sx={{ textAlign: 'center', height: '100%' }}>
        <CardContent sx={{ py: 1.5 }}>
          <Typography variant="caption" color="text.secondary" display="block">
            {label}
          </Typography>
          <Typography variant="h6" sx={{ color: color ?? 'text.primary', fontWeight: 700 }}>
            {value}
            {unit && (
              <Typography component="span" variant="caption" color="text.secondary" ml={0.3}>
                {unit}
              </Typography>
            )}
          </Typography>
        </CardContent>
      </Card>
    </Tooltip>
  );
}

function StudyTaskPanel({
  condition,
  dataset,
  sessionStart,
}: {
  condition: string;
  dataset: string;
  sessionStart: number;
}) {
  const [answer, setAnswer] = useState('');
  const [confidence, setConfidence] = useState<number>(3);
  const [submitted, setSubmitted] = useState(false);
  const taskStarted = useRef(false);

  const handleFocus = () => {
    if (!taskStarted.current) {
      taskStarted.current = true;
      logEvent(condition, dataset, 'task_start', {});
    }
  };

  const handleSubmit = () => {
    if (!answer.trim()) return;
    const elapsed = Date.now() - sessionStart;
    logEvent(condition, dataset, 'task_submit', { answer, confidence, time_to_answer_ms: elapsed });
    setSubmitted(true);
  };

  return (
    <Card variant="outlined" sx={{ mb: 3, borderColor: 'primary.light' }}>
      <CardContent>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1, color: 'primary.main' }}>
          Study Task
        </Typography>
        <Typography variant="body2" mb={2}>
          Looking at the data for this class, which concept do students struggle with most?
          Which students would you prioritize for office hours, and why?
        </Typography>
        {!submitted ? (
          <>
            <TextField
              label="Your answer"
              multiline
              rows={3}
              fullWidth
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onFocus={handleFocus}
              placeholder="Describe which concept(s) you'd address and which students you'd target..."
              sx={{ mb: 2 }}
            />
            <Typography variant="caption" color="text.secondary" gutterBottom display="block">
              Confidence in your answer: {confidence} / 5
            </Typography>
            <Slider
              min={1}
              max={5}
              step={1}
              marks
              value={confidence}
              onChange={(_e, v) => setConfidence(v as number)}
              sx={{ mb: 2, maxWidth: 300 }}
            />
            <Button variant="contained" onClick={handleSubmit} disabled={!answer.trim()}>
              Submit answer
            </Button>
          </>
        ) : (
          <Alert severity="success">
            Answer recorded. Thank you! You can continue exploring the dashboard.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

export default function InstructorDashboard() {
  const [searchParams] = useSearchParams();
  const condition = searchParams.get('condition') ?? 'B';
  const isControlCondition = condition === 'A';
  const isStudyMode = searchParams.get('condition') !== null;
  const sessionStart = useRef(Date.now());

  const [datasets, setDatasets] = useState<string[]>([]);
  const [selectedTab, setSelectedTab] = useState(0);
  const [vizData, setVizData] = useState<DatasetSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available datasets on mount
  useEffect(() => {
    const api = getApiBase();
    fetch(`${api}/api/visualization/datasets`)
      .then((r) => r.json())
      .then((data: { datasets: string[] }) => {
        setDatasets(data.datasets);
      })
      .catch(() => {
        // Fallback to known datasets
        setDatasets(['mohler', 'digiklausur', 'kaggle_asag']);
      });
  }, []);

  // Load selected dataset
  const selectedDataset = datasets[selectedTab] ?? '';

  useEffect(() => {
    if (!selectedDataset) return;
    setLoading(true);
    setError(null);
    const api = getApiBase();
    fetch(`${api}/api/visualization/datasets/${selectedDataset}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: DatasetSummaryResponse) => {
        setVizData(data);
        setLoading(false);
        logEvent(condition, selectedDataset, 'tab_change', { dataset: selectedDataset });
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, [selectedDataset, condition]);

  // Log page view on mount
  useEffect(() => {
    logEvent(condition, '', 'page_view', { session_id: SESSION_ID, is_study: isStudyMode });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleExportLog = () => {
    const blob = new Blob([exportStudyLog()], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `study-log-${SESSION_ID.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const specs = vizData?.visualizations ?? [];
  const summary = findSpec(specs, 'class_summary');
  const summaryData = (summary?.data ?? {}) as Record<string, number>;

  const maeReduction = summaryData.mae_reduction_pct ?? vizData?.mae_reduction_pct ?? 0;
  const wilcoxonP = summaryData.wilcoxon_p ?? vizData?.wilcoxon_p ?? 1;
  const c5Mae = summaryData.c5_mae ?? vizData?.metrics.C5_fix.mae ?? 0;
  const cllmMae = summaryData.c_llm_mae ?? vizData?.metrics.C_LLM.mae ?? 0;

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            ConceptGrade — Instructor Analytics Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Knowledge Graph-grounded grading diagnostics
            {isStudyMode && ` · Study condition: ${condition}`}
          </Typography>
        </Box>
        <Box display="flex" gap={1} alignItems="center">
          <Tooltip title="Refresh data">
            <IconButton
              onClick={() => {
                setVizData(null);
                setSelectedTab((t) => t); // trigger reload
              }}
              size="small"
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Dataset tabs */}
      {datasets.length > 0 && (
        <Tabs
          value={selectedTab}
          onChange={(_e, v: number) => setSelectedTab(v)}
          sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}
        >
          {datasets.map((ds) => (
            <Tab key={ds} label={DATASET_LABELS[ds] ?? ds} />
          ))}
        </Tabs>
      )}

      {/* Study task panel */}
      {isStudyMode && (
        <StudyTaskPanel
          condition={condition}
          dataset={selectedDataset}
          sessionStart={sessionStart.current}
        />
      )}

      {loading && (
        <Box display="flex" justifyContent="center" py={8}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load data for "{selectedDataset}": {error}. Make sure the NestJS backend is
          running and eval results are in packages/concept-aware/data/.
        </Alert>
      )}

      {!loading && !error && vizData && (
        <>
          {/* Summary card row — visible in ALL conditions */}
          <Grid container spacing={2} mb={3}>
            <Grid item xs={6} sm={3} md={2}>
              <MetricCard label="Total Answers" value={vizData.n} tooltip="Number of student answers in this dataset" />
            </Grid>
            <Grid item xs={6} sm={3} md={2}>
              <MetricCard
                label="C5 MAE"
                value={c5Mae.toFixed(3)}
                color="#16a34a"
                tooltip="ConceptGrade Mean Absolute Error — lower is better"
              />
            </Grid>
            <Grid item xs={6} sm={3} md={2}>
              <MetricCard
                label="Baseline MAE"
                value={cllmMae.toFixed(3)}
                color="#dc2626"
                tooltip="Pure LLM baseline Mean Absolute Error"
              />
            </Grid>
            <Grid item xs={6} sm={3} md={2}>
              <MetricCard
                label="MAE Reduction"
                value={maeReduction.toFixed(1)}
                unit="%"
                color={maeReduction > 0 ? '#16a34a' : '#dc2626'}
                tooltip="Percentage improvement in MAE over LLM baseline"
              />
            </Grid>
            <Grid item xs={6} sm={3} md={2}>
              <MetricCard
                label="Wilcoxon p"
                value={wilcoxonP < 0.001 ? '<0.001' : wilcoxonP.toFixed(3)}
                color={wilcoxonP < 0.05 ? '#16a34a' : '#9ca3af'}
                tooltip="Paired Wilcoxon signed-rank test p-value (< 0.05 = significant)"
              />
            </Grid>
            <Grid item xs={6} sm={3} md={2}>
              <MetricCard
                label="Pearson r (C5)"
                value={(vizData.metrics.C5_fix.r ?? 0).toFixed(3)}
                color="#3b82f6"
                tooltip="ConceptGrade Pearson correlation with human grades"
              />
            </Grid>
          </Grid>

          {/* Insights from summary spec */}
          {summary?.insights?.map((insight, i) => (
            <Alert key={i} severity="info" sx={{ mb: 1 }}>
              {insight}
            </Alert>
          ))}

          {/* Charts — only visible in condition B */}
          {!isControlCondition && (
            <>
              <Divider sx={{ my: 2 }} />

              {/* Bloom's + SOLO row */}
              <Grid container spacing={3} mb={3}>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ p: 2, height: '100%' }}>
                    {findSpec(specs, 'blooms_dist') && (
                      <BloomsBarChart
                        spec={findSpec(specs, 'blooms_dist')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                    )}
                    {findSpec(specs, 'blooms_dist')?.insights?.map((ins, i) => (
                      <Typography key={i} variant="caption" color="text.secondary" display="block" mt={1}>
                        {ins}
                      </Typography>
                    ))}
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ p: 2, height: '100%' }}>
                    {findSpec(specs, 'solo_dist') && (
                      <SoloBarChart
                        spec={findSpec(specs, 'solo_dist')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                    )}
                    {findSpec(specs, 'solo_dist')?.insights?.map((ins, i) => (
                      <Typography key={i} variant="caption" color="text.secondary" display="block" mt={1}>
                        {ins}
                      </Typography>
                    ))}
                  </Card>
                </Grid>
              </Grid>

              {/* Score comparison + Chain coverage */}
              <Grid container spacing={3} mb={3}>
                <Grid item xs={12} md={7}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    {findSpec(specs, 'score_comparison') && (
                      <ScoreComparisonChart
                        spec={findSpec(specs, 'score_comparison')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                    )}
                  </Card>
                </Grid>
                <Grid item xs={12} md={5}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    {findSpec(specs, 'chain_coverage_dist') && (
                      <ChainCoverageChart
                        spec={findSpec(specs, 'chain_coverage_dist')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                    )}
                    {findSpec(specs, 'chain_coverage_dist')?.insights?.map((ins, i) => (
                      <Typography key={i} variant="caption" color="text.secondary" display="block" mt={1}>
                        {ins}
                      </Typography>
                    ))}
                  </Card>
                </Grid>
              </Grid>

              {/* Concept frequency — full width */}
              <Grid container mb={3}>
                <Grid item xs={12}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    {findSpec(specs, 'concept_frequency') && (
                      <ConceptFrequencyChart
                        spec={findSpec(specs, 'concept_frequency')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                    )}
                    {findSpec(specs, 'concept_frequency')?.insights?.map((ins, i) => (
                      <Typography key={i} variant="caption" color="text.secondary" display="block" mt={1}>
                        {ins}
                      </Typography>
                    ))}
                  </Card>
                </Grid>
              </Grid>

              {/* Per-sample score table (API spec score_scatter) */}
              {findSpec(specs, 'score_scatter') && (
                <Grid container mb={3}>
                  <Grid item xs={12}>
                    <Card variant="outlined" sx={{ p: 2 }}>
                      <ScoreSamplesTable
                        spec={findSpec(specs, 'score_scatter')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                      {findSpec(specs, 'score_scatter')?.insights?.map((ins, i) => (
                        <Typography key={i} variant="caption" color="text.secondary" display="block" mt={1}>
                          {ins}
                        </Typography>
                      ))}
                    </Card>
                  </Grid>
                </Grid>
              )}

              {/* Radar + Misconception heatmap (backend always sends specs; may be empty placeholders) */}
              <Grid container spacing={3} mb={3}>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    {findSpec(specs, 'student_radar') && (
                      <StudentRadarChart
                        spec={findSpec(specs, 'student_radar')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                    )}
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    {findSpec(specs, 'misconception_heatmap') && (
                      <MisconceptionHeatmap
                        spec={findSpec(specs, 'misconception_heatmap')!}
                        condition={condition}
                        dataset={selectedDataset}
                      />
                    )}
                  </Card>
                </Grid>
              </Grid>
            </>
          )}

          {/* Study log export — only in study mode */}
          {isStudyMode && (
            <Box mt={3} display="flex" gap={2} alignItems="center">
              <Button
                variant="outlined"
                size="small"
                startIcon={<DownloadIcon />}
                onClick={handleExportLog}
              >
                Export study log (JSON)
              </Button>
              <Typography variant="caption" color="text.secondary">
                Session: {SESSION_ID.slice(0, 8)}
              </Typography>
            </Box>
          )}
        </>
      )}
    </Container>
  );
}
