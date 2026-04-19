import DownloadIcon from '@mui/icons-material/Download';
import RefreshIcon from '@mui/icons-material/Refresh';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Collapse,
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
  ConceptKGPanel,
  CrossDatasetComparisonChart,
  MisconceptionHeatmap,
  ScoreComparisonChart,
  ScoreSamplesTable,
  SoloBarChart,
  StudentAnswerPanel,
  StudentRadarChart,
} from '../components/charts';
import { SUSQuestionnaire } from '../components/charts/SUSQuestionnaire';
import { RubricEditorPanel } from '../components/charts/RubricEditorPanel';
import { DatasetSummaryResponse, VisualizationSpec } from '../common/visualization.types';
import { DashboardProvider, useDashboard } from '../contexts/DashboardContext';
import {
  SESSION_ID,
  exportStudyLog,
  logEvent,
  setStudyApiBase,
  setDualWriteFailureHandler,
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
  onTaskSubmitted,
}: {
  condition: string;
  dataset: string;
  sessionStart: number;
  onTaskSubmitted: () => void;
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
    logEvent(condition, dataset, 'task_submit', { answer, confidence, time_to_answer_ms: elapsed, event_subtype: 'main_task' });
    setSubmitted(true);
    onTaskSubmitted();
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
            Answer recorded. Please complete the usability questionnaire below.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

/** Inner dashboard — must be inside DashboardProvider */
function InstructorDashboardInner() {
  const [searchParams] = useSearchParams();
  const rawCondition = searchParams.get('condition');
  // Runtime guard: reject invalid condition strings to prevent silent data pollution.
  // Unknown values coerce to 'B' (treatment) so the study never silently mislabels events.
  const condition = (rawCondition === 'A' || rawCondition === 'B') ? rawCondition : (rawCondition !== null ? 'B' : 'B');
  const isControlCondition = condition === 'A';
  const isStudyMode = rawCondition !== null;
  const sessionStart = useRef(Date.now());

  const [datasets, setDatasets] = useState<string[]>([]);
  const [selectedTab, setSelectedTab] = useState(0);
  // Incrementing key forces the fetch useEffect to re-run on manual refresh
  // without changing selectedTab (which would be a no-op if already on the same tab).
  const [fetchKey, setFetchKey] = useState(0);
  const [vizData, setVizData] = useState<DatasetSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // KG panel visibility — local UI state (not shared selection state)
  const [showKG, setShowKG] = useState(false);
  // Onboarding guide — collapsed by default to avoid cognitive overload on first view
  const [helpOpen, setHelpOpen] = useState(false);
  // Backend reachability — shown as a banner so the study facilitator can act before wasting a participant's time
  const [backendDown, setBackendDown] = useState(false);
  // Fatal logging failure — both localStorage AND backend POST failed for the same event.
  // Shows a blocking overlay; participant must resolve before continuing (IRB requirement).
  const [logFailure, setLogFailure] = useState(false);
  // Whether the main study task has been submitted — triggers SUS questionnaire + rubric editor
  const [taskSubmitted, setTaskSubmitted] = useState(false);
  // Accumulated set of CONTRADICTS node IDs seen across all trace expansions this session.
  // Updated whenever a CONTRADICTS step is interacted with in VerifierReasoningPanel.
  // Passed to RubricEditorPanel for causal proximity attribution on rubric edits.
  const [sessionContradictsNodes, setSessionContradictsNodes] = useState<string[]>([]);

  // Linking & brushing via DashboardContext
  const { selectedConcept, selectedSeverity, selectConcept, clearAll, recentContradicts, traceOpen } = useDashboard();

  // Mirror new entries from the rolling recentContradicts window into the session-scoped
  // accumulated set. recentContradicts only holds the last 60 s; we use timestamps to
  // detect entries we haven't yet added to sessionContradictsNodes.
  const seenContradictTimestamps = React.useRef(new Set<number>());
  React.useEffect(() => {
    for (const entry of recentContradicts) {
      if (!seenContradictTimestamps.current.has(entry.timestamp_ms)) {
        seenContradictTimestamps.current.add(entry.timestamp_ms);
        setSessionContradictsNodes(prev =>
          prev.includes(entry.nodeId) ? prev : [...prev, entry.nodeId],
        );
      }
    }
  }, [recentContradicts]);

  // Load available datasets on mount
  useEffect(() => {
    const api = getApiBase();
    fetch(`${api}/api/visualization/datasets`)
      .then((r) => r.json())
      .then((data: { datasets: string[] }) => {
        setDatasets(data.datasets);
      })
      .catch(() => {
        setDatasets(['mohler', 'digiklausur', 'kaggle_asag']);
      });
  }, []);

  const selectedDataset = datasets[selectedTab] ?? '';

  const handleConceptClick = (concept: string, severity: string) => {
    if (selectedConcept === concept) {
      selectConcept(null, null);
      setShowKG(false);
    } else {
      selectConcept(concept, severity);
      setShowKG(false);
    }
  };

  // Load selected dataset — reset linking state when dataset changes
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
        clearAll();
        setShowKG(false);
        logEvent(condition, selectedDataset, 'tab_change', { dataset: selectedDataset });
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, [selectedDataset, condition, fetchKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Register backend log endpoint, emit page_view, and run a health probe on mount.
  // The health probe gives the study facilitator an immediate signal if the backend
  // is unreachable before investing a participant's time in the session.
  useEffect(() => {
    setStudyApiBase(apiBase);
    setDualWriteFailureHandler(() => setLogFailure(true));
    logEvent(condition, '', 'page_view', { session_id: SESSION_ID, is_study: isStudyMode });
    fetch(`${apiBase}/api/study/health`)
      .then((r) => setBackendDown(!r.ok))
      .catch(() => setBackendDown(true));
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
  const apiBase = getApiBase();

  const handleCloseAnswerPanel = () => {
    selectConcept(null, null);
    setShowKG(false);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Backend health banner — visible only to the study facilitator when the backend is unreachable */}
      {backendDown && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <strong>Backend unreachable.</strong> The NestJS API at <code>{apiBase}</code> did not respond.
          Study log events will be stored in localStorage only — server-side backup is offline.
          Check that the backend is running before beginning a participant session.
        </Alert>
      )}
      {/* Fatal dual-write failure overlay — blocks session continuation (IRB requirement).
          Shown when BOTH localStorage AND the backend POST fail for the same event,
          meaning the session data cannot be recovered. Participant must resolve before continuing. */}
      {logFailure && (
        <Alert severity="error" sx={{ mb: 2, border: '2px solid #dc2626' }}>
          <strong>⚠ Logging error — session data cannot be recorded.</strong> Both local storage and
          the server log endpoint are unavailable. This is likely caused by a browser extension
          blocking the logging API, or a strict private-browsing mode with zero storage quota.
          <br /><strong>Please disable ad-blockers / tracking prevention and reload the page before continuing.</strong>
          This session cannot be used for the study until logging is restored.
        </Alert>
      )}
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
                setFetchKey((k) => k + 1);
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
          onTaskSubmitted={() => setTaskSubmitted(true)}
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
            <Grid item xs={6} sm={4} md={true}>
              <MetricCard label="Total Answers" value={vizData.n} tooltip="Number of student answers in this dataset" />
            </Grid>
            <Grid item xs={6} sm={4} md={true}>
              <MetricCard
                label="C5 MAE"
                value={c5Mae.toFixed(3)}
                color="#16a34a"
                tooltip="ConceptGrade Mean Absolute Error — lower is better"
              />
            </Grid>
            <Grid item xs={6} sm={4} md={true}>
              <MetricCard
                label="Baseline MAE"
                value={cllmMae.toFixed(3)}
                color="#dc2626"
                tooltip="Pure LLM baseline Mean Absolute Error"
              />
            </Grid>
            <Grid item xs={6} sm={4} md={true}>
              <MetricCard
                label="MAE Reduction"
                value={maeReduction.toFixed(1)}
                unit="%"
                color={maeReduction > 0 ? '#16a34a' : '#dc2626'}
                tooltip="Percentage improvement in MAE over LLM baseline"
              />
            </Grid>
            <Grid item xs={6} sm={4} md={true}>
              <MetricCard
                label="Wilcoxon p"
                value={wilcoxonP < 0.001 ? '<0.001' : wilcoxonP.toFixed(3)}
                color={wilcoxonP < 0.05 ? '#16a34a' : '#9ca3af'}
                tooltip="Paired Wilcoxon signed-rank test p-value (< 0.05 = significant)"
              />
            </Grid>
            <Grid item xs={6} sm={4} md={true}>
              <MetricCard
                label="Pearson r (C5)"
                value={(vizData.metrics.C5_fix.r ?? 0).toFixed(3)}
                color="#3b82f6"
                tooltip="ConceptGrade Pearson correlation with human grades"
              />
            </Grid>
            <Grid item xs={6} sm={4} md={true}>
              <MetricCard
                label="No Matched Concepts"
                value={summaryData.total_misconceptions ?? 0}
                color="#f59e0b"
                tooltip="Answers where no KG concepts were matched — proxy for missed content coverage"
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

              {/* Onboarding guide — collapsed by default to reduce first-impression overload */}
              <Box mb={2}>
                <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    New to this dashboard?
                  </Typography>
                  <Button
                    size="small"
                    variant="text"
                    onClick={() => setHelpOpen((o) => !o)}
                    sx={{ fontSize: 10, py: 0.25, px: 0.75, minWidth: 'auto', textTransform: 'none' }}
                  >
                    {helpOpen ? 'Hide guide ▲' : 'Show interaction guide ▼'}
                  </Button>
                </Box>
                <Collapse in={helpOpen}>
                  <Alert severity="info" sx={{ py: 0.75 }}>
                    <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 0.5 }}>
                      4 key interactions — start here:
                    </Typography>
                    {[
                      '1.  To investigate a class-wide misconception, click its heatmap cell → see affected students, pre-filtered by severity.',
                      '2.  To understand why a concept was missed, click the KG button → explore its prerequisites in the knowledge graph (drag nodes to rearrange).',
                      '3.  To see which concepts drove a score gap, expand any score table row → concept gap analysis loads and KG nodes colour green / red / grey.',
                      '4.  To focus on a specific score range, click a Radar quartile chip → the answer list filters to that group.',
                    ].map((tip) => (
                      <Typography key={tip} variant="caption" display="block" sx={{ lineHeight: 1.7 }}>
                        {tip}
                      </Typography>
                    ))}
                  </Alert>
                </Collapse>
              </Box>

              {/* Cross-dataset slopegraph — domain complexity narrative */}
              <Grid container mb={3}>
                <Grid item xs={12}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    <CrossDatasetComparisonChart apiBase={apiBase} condition={condition} />
                  </Card>
                </Grid>
              </Grid>

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

              {/* Per-sample score table with XAI provenance */}
              {findSpec(specs, 'score_scatter') && (
                <Grid container mb={3}>
                  <Grid item xs={12}>
                    <Card variant="outlined" sx={{ p: 2 }}>
                      <ScoreSamplesTable
                        spec={findSpec(specs, 'score_scatter')!}
                        condition={condition}
                        dataset={selectedDataset}
                        apiBase={apiBase}
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

              {/* Radar + Misconception heatmap (linked — heatmap drives answer panel) */}
              <Grid container spacing={3} mb={2}>
                <Grid item xs={12} md={5}>
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
                <Grid item xs={12} md={7}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    {findSpec(specs, 'misconception_heatmap') && (
                      <MisconceptionHeatmap
                        spec={findSpec(specs, 'misconception_heatmap')!}
                        condition={condition}
                        dataset={selectedDataset}
                        selectedConcept={selectedConcept}
                        onCellClick={handleConceptClick}
                      />
                    )}
                    {findSpec(specs, 'misconception_heatmap')?.insights?.map((ins, i) => (
                      <Typography key={i} variant="caption" color="text.secondary" display="block" mt={1}>
                        {ins}
                      </Typography>
                    ))}
                  </Card>
                </Grid>
              </Grid>

              {/* Linking panels — shown when a concept cell is selected */}
              {selectedConcept && (
                <Grid container spacing={3} mb={3}>
                  {/* Student Answer Panel */}
                  <Grid item xs={12} md={showKG ? 6 : 12}>
                    <StudentAnswerPanel
                      dataset={selectedDataset}
                      conceptId={selectedConcept}
                      defaultSeverity={selectedSeverity}
                      apiBase={apiBase}
                      onClose={handleCloseAnswerPanel}
                      onShowKG={() => setShowKG(true)}
                      studyCondition={isStudyMode ? condition : undefined}
                      tracePanelOpen={traceOpen}
                      kgPanelOpen={showKG}
                    />
                  </Grid>

                  {/* KG Subgraph Panel */}
                  {showKG && (
                    <Grid item xs={12} md={6}>
                      <ConceptKGPanel
                        dataset={selectedDataset}
                        conceptId={selectedConcept}
                        apiBase={apiBase}
                        onClose={() => setShowKG(false)}
                        condition={condition}
                      />
                    </Grid>
                  )}
                </Grid>
              )}
            </>
          )}

          {/* Rubric editor — shown after task submitted in BOTH conditions.
              Condition B: passes accumulated sessionContradictsNodes for trace attribution.
              Condition A: passes empty array (no trace context) — provides a true
              between-condition comparison of what educators edit without trace guidance. */}
          {isStudyMode && taskSubmitted && (
            <RubricEditorPanel
              condition={condition as 'A' | 'B'}
              dataset={selectedDataset}
              specs={vizData?.visualizations ?? []}
              sessionContradictsNodes={condition === 'B' ? sessionContradictsNodes : []}
            />
          )}

          {/* SUS questionnaire — appears once main task is submitted */}
          {isStudyMode && taskSubmitted && (
            <SUSQuestionnaire
              condition={condition}
              dataset={selectedDataset}
              sessionStart={sessionStart.current}
            />
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

/** Wrap the inner dashboard with DashboardProvider so all child components share selection state */
export default function InstructorDashboard() {
  return (
    <DashboardProvider>
      <InstructorDashboardInner />
    </DashboardProvider>
  );
}
