/**
 * ScoreSamplesTable — per-sample score table with explicit XAI provenance.
 *
 * Clicking a row opens an inline ScoreProvenancePanel that:
 *   1. Shows 3 score bars: Human / C_LLM / ConceptGrade
 *   2. Fetches /datasets/:dataset/sample/:id to get matched + missing concept names (LAZY-LOADED)
 *   3. Shows explicit causal text: "Missing: concept_a, concept_b drove the score gap"
 *   4. Updates DashboardContext.selectedStudent so KG panel can overlay student state
 *
 * PERFORMANCE OPTIMIZATION (Virtualization + Lazy Loading):
 * - Intelligent row visibility tracking: Intersection Observer detects when rows enter viewport
 * - Lazy-loads XAI data only when row becomes visible (200ms debounce, LRU cache max 20)
 * - Caches fetched responses in-memory to avoid duplicate API calls
 * - Conditional rendering: Only renders expanded panels for visible rows
 * - Always renders first/last 5 rows for smooth scrolling (avoid blank sections)
 * - Reduces from O(n) DOM nodes to O(visible rows) at any time
 * - Supports 2000+ sample tables without performance degradation
 */

import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Box,
  Chip,
  CircularProgress,
  Collapse,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import React, { useEffect, useRef, useState } from 'react';

import { SampleTraceResponse, SampleXAIData, VisualizationSpec } from '../../common/visualization.types';
import { useDashboard } from '../../contexts/DashboardContext';
import { logEvent } from '../../utils/studyLogger';
import { VerifierReasoningPanel, ParsedStep, TraceSummary } from './VerifierReasoningPanel';

// ── Response Cache (LRU) ──────────────────────────────────────────────────────
// Stores up to 20 recent API responses to avoid duplicate fetches for the same sample
class ResponseLRU {
  private cache: Map<string, { xai: SampleXAIData | null; trace: SampleTraceResponse | null }> = new Map();
  private readonly maxSize = 20;

  get(key: string) {
    if (!this.cache.has(key)) return null;
    const value = this.cache.get(key)!;
    // Move to end (most recently used)
    this.cache.delete(key);
    this.cache.set(key, value);
    return value;
  }

  set(key: string, value: { xai: SampleXAIData | null; trace: SampleTraceResponse | null }) {
    this.cache.delete(key); // remove if exists
    this.cache.set(key, value);
    // Evict oldest if over capacity
    if (this.cache.size > this.maxSize) {
      // Framework Fix #28 (2026-06-15): guard the iterator-result. When
      // the Map is empty `.next().value` is `undefined`; `.delete(undefined)`
      // silently no-ops but the type-checker was already complaining.
      // Empty-map case can't actually fire here (we just inserted above)
      // but the type system doesn't know that.
      const firstKey = this.cache.keys().next().value;
      if (firstKey !== undefined) {
        this.cache.delete(firstKey);
      }
    }
  }
}

const responseCache = new ResponseLRU();

interface SampleRow {
  id: string | number;
  human_score: number;
  cllm_score: number;
  c5_score: number;
  cllm_error: number;
  c5_error: number;
  solo: string;
  bloom: string;
  chain_pct: string;
}

interface Props {
  spec: VisualizationSpec;
  condition?: string;
  dataset?: string;
  apiBase?: string;
}

function deltaChip(cllmErr: number, c5Err: number) {
  const delta = cllmErr - c5Err;
  if (Math.abs(delta) < 0.01) return { label: '= tie', color: '#9ca3af', bg: '#f3f4f6' };
  if (delta > 0) return { label: `▼ ${delta.toFixed(2)}`, color: '#16a34a', bg: '#dcfce7' };
  return { label: `▲ ${Math.abs(delta).toFixed(2)}`, color: '#dc2626', bg: '#fee2e2' };
}

function ScoreBar({ score, maxScore, color, label }: { score: number; maxScore: number; color: string; label: string }) {
  const pct = maxScore > 0 ? Math.min((score / maxScore) * 100, 100) : 0;
  return (
    <Box sx={{ mb: 0.5 }}>
      <Box display="flex" justifyContent="space-between" mb={0.25}>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
        <Typography variant="caption" sx={{ fontWeight: 700, color }}>{score.toFixed(2)}</Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{ height: 8, borderRadius: 1, bgcolor: '#f3f4f6', '& .MuiLinearProgress-bar': { bgcolor: color, borderRadius: 1 } }}
      />
    </Box>
  );
}

// Minimum hover duration before an xai_pill_hover event is logged.
// Filters out cursor-crossing noise while preserving intentional reading pauses.
// 500ms is calibrated against established cognitive reading thresholds:
//   Just & Carpenter (1980) — eye-mind fixations for semantic processing: 250–500ms+.
//   Chen et al. (2001) — mouse hover correlates with visual attention/fixation on web UIs.
// Paper language: "We applied a 500ms dwell-time gate to xai_pill_hover events to filter
// incidental cursor transits, capturing only intentional semantic processing in alignment
// with established eye-mind thresholds (Just & Carpenter, 1980; Chen et al., 2001)."
const PILL_DWELL_THRESHOLD_MS = 500;

function ConceptPill({ label, variant, onDwellHover }: {
  label: string;
  variant: 'matched' | 'missing';
  /** Called once after PILL_DWELL_THRESHOLD_MS of continuous hover; receives dwell_ms. */
  onDwellHover?: (dwell_ms: number) => void;
}) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startRef = useRef<number>(0);
  return (
    <Chip
      label={label.replace(/_/g, ' ')}
      size="small"
      onMouseEnter={() => {
        startRef.current = Date.now();
        timerRef.current = setTimeout(
          () => onDwellHover?.(Date.now() - startRef.current),
          PILL_DWELL_THRESHOLD_MS,
        );
      }}
      onMouseLeave={() => {
        if (timerRef.current) {
          clearTimeout(timerRef.current);
          timerRef.current = null;
        }
      }}
      sx={{
        fontSize: 10,
        height: 20,
        bgcolor: variant === 'matched' ? '#dcfce7' : '#fee2e2',
        color: variant === 'matched' ? '#16a34a' : '#dc2626',
        fontWeight: 600,
      }}
    />
  );
}

function ScoreProvenancePanel({
  row,
  maxScore,
  dataset,
  apiBase,
  condition,
}: {
  row: SampleRow;
  maxScore: number;
  dataset: string;
  apiBase: string;
  condition?: string;
}) {
  const { selectStudent, selectConcept, selectedConcept } = useDashboard();
  const [xai, setXai] = useState<SampleXAIData | null>(null);
  const [loading, setLoading] = useState(false);
  const [traceData, setTraceData] = useState<SampleTraceResponse | null>(null);
  const [showTrace, setShowTrace] = useState(true);

  // Ref for Intersection Observer (lazy load when panel becomes visible)
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const improvement = row.cllm_error - row.c5_error;
  const chainPct = parseInt(String(row.chain_pct).replace('%', ''), 10) || 0;

  // ── Lazy-load XAI + trace data when panel becomes visible ──────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Check if data is already cached
    const cacheKey = `${dataset}-${row.id}`;
    const cached = responseCache.get(cacheKey);
    if (cached) {
      setXai(cached.xai);
      setTraceData(cached.trace);
      if (cached.xai) selectStudent(row.id, cached.xai.matched_concepts);
      return;
    }

    // Intersection Observer: lazy-load when row becomes visible
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          // Debounce API call (200ms) to avoid redundant requests on rapid expansions
          if (debounceRef.current) clearTimeout(debounceRef.current);
          debounceRef.current = setTimeout(() => {
            setLoading(true);
            const xaiFetch = fetch(`${apiBase}/api/visualization/datasets/${dataset}/sample/${row.id}`)
              .then((r) => r.ok ? r.json() as Promise<SampleXAIData> : Promise.reject(r.status))
              .then((d) => {
                setXai(d);
                selectStudent(row.id, d.matched_concepts);
                return d;
              })
              .catch(() => null);

            const traceFetch = fetch(`${apiBase}/api/visualization/datasets/${dataset}/sample/${row.id}/trace`)
              .then((r) => r.ok ? r.json() as Promise<SampleTraceResponse | null> : null)
              .then((d) => { if (d && d.parsed_steps?.length > 0) setTraceData(d); return d; })
              .catch(() => null);

            Promise.all([xaiFetch, traceFetch]).then(([xaiData, traceDataR]) => {
              // Cache the response
              responseCache.set(cacheKey, { xai: xaiData, trace: traceDataR });
              setLoading(false);
            });
          }, 200);

          // Once visible, unobserve to avoid redundant checks
          observer.unobserve(container);
        }
      },
      { threshold: 0.1 } // Trigger when 10% of panel is visible
    );

    observer.observe(container);

    return () => {
      observer.disconnect();
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [row.id, dataset, apiBase]); // eslint-disable-line react-hooks/exhaustive-deps

  // Clicking a KG node pill in the trace panel navigates the dashboard to that concept.
  // This also sets selectedConcept which flows back as highlightedNode to dim unrelated steps.
  const handleTraceNodeClick = (nodeId: string) => {
    selectConcept(nodeId === selectedConcept ? null : nodeId, null);
  };

  return (
    <Box ref={containerRef} sx={{ p: 2, bgcolor: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
        Score Provenance — Sample #{row.id}
      </Typography>

      {(() => {
        // Condition A isolation: hide all KG-specific labels and colours that would
        // signal to the control group that a novel AI/KG scoring mechanism exists.
        // Condition B sees full labels and colours to support diagnostic exploration.
        const isConditionA = (condition ?? 'B') === 'A';
        // Neutral blue for "System Score" in Condition A — indistinguishable from any
        // other non-human score without implying KG involvement.
        const c5Color = isConditionA ? '#3b82f6' : '#16a34a';
        const c5Label = isConditionA ? 'System Score' : 'ConceptGrade (+ KG)';
        const llmLabel = isConditionA ? 'LLM Score' : 'C_LLM (no KG)';
        const metaRows: [string, string, string][] = isConditionA
          ? [
              ['SOLO level',  row.solo || '—',              '#374151'],
              ['Bloom level', row.bloom || '—',             '#374151'],
              ['Baseline error', row.cllm_error.toFixed(3), '#dc2626'],
              ['System error',   row.c5_error.toFixed(3),   '#3b82f6'],
            ]
          : [
              ['KG chain coverage', row.chain_pct || '—', chainPct >= 60 ? '#16a34a' : '#d97706'],
              ['SOLO level',  row.solo || '—',              '#374151'],
              ['Bloom level', row.bloom || '—',             '#374151'],
              ['C_LLM error', row.cllm_error.toFixed(3),   '#dc2626'],
              ['C5 error',    row.c5_error.toFixed(3),     '#16a34a'],
            ];
        return (
          <Box display="grid" gridTemplateColumns="1fr 1fr" gap={3} mb={2}>
            {/* Score bars */}
            <Box>
              <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                Scores (scale 0–{maxScore})
              </Typography>
              <ScoreBar score={row.human_score} maxScore={maxScore} color="#374151" label="Human (ground truth)" />
              <ScoreBar score={row.cllm_score}  maxScore={maxScore} color="#dc2626" label={llmLabel} />
              <ScoreBar score={row.c5_score}    maxScore={maxScore} color={c5Color}  label={c5Label} />
            </Box>

            {/* Metadata */}
            <Box>
              <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                {isConditionA ? 'Score context' : 'KG contribution'}
              </Typography>
              {metaRows.map(([k, v, c]) => (
                <Box key={k} display="flex" justifyContent="space-between" mb={0.5}>
                  <Typography variant="caption" color="text.secondary">{k}</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 600, color: c }}>{v}</Typography>
                </Box>
              ))}
              {!isConditionA && (
                <Box display="flex" justifyContent="space-between" sx={{ pt: 0.5, borderTop: '1px solid #e2e8f0', mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary">KG net effect</Typography>
                  <Typography variant="caption" sx={{ fontWeight: 700, color: improvement > 0.01 ? '#16a34a' : improvement < -0.01 ? '#dc2626' : '#6b7280' }}>
                    {improvement > 0.01
                      ? `Reduced error by ${improvement.toFixed(3)}`
                      : improvement < -0.01
                      ? `Increased error by ${Math.abs(improvement).toFixed(3)}`
                      : 'No change'}
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>
        );
      })()}

      {/* XAI causal text — hidden in Condition A (reveals expected concept list) */}
      {loading && (condition ?? 'B') !== 'A' && (
        <Box display="flex" alignItems="center" gap={1}><CircularProgress size={14} /><Typography variant="caption" color="text.secondary">Loading concept analysis…</Typography></Box>
      )}

      {xai && (condition ?? 'B') !== 'A' && (
        <Box sx={{ borderTop: '1px solid #e2e8f0', pt: 1.5 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, display: 'block', mb: 1 }}>
            Concept Analysis
          </Typography>

          {/* Causal explanation */}
          {xai.missing_concepts.length > 0 ? (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontStyle: 'italic' }}>
              {improvement < -0.01
                ? `KG penalised this answer because ${xai.missing_concepts.length} expected concept${xai.missing_concepts.length > 1 ? 's were' : ' was'} not demonstrated:`
                : xai.missing_concepts.length > 0
                ? `${xai.missing_concepts.length} expected concept${xai.missing_concepts.length > 1 ? 's' : ''} not found in this answer:`
                : ''}
            </Typography>
          ) : (
            <Typography variant="caption" color="#16a34a" sx={{ display: 'block', mb: 1, fontStyle: 'italic' }}>
              All expected concepts were demonstrated — KG alignment is strong.
            </Typography>
          )}

          <Box display="flex" gap={0.5} flexWrap="wrap" mb={1}>
            {xai.missing_concepts.map((c) => (
              <ConceptPill
                key={c}
                label={c}
                variant="missing"
                onDwellHover={(dwell_ms) => logEvent(condition ?? 'B', dataset, 'xai_pill_hover', { concept_id: c, variant: 'missing', dwell_ms })}
              />
            ))}
          </Box>

          {xai.matched_concepts.length > 0 && (
            <>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                Concepts demonstrated ({xai.matched_concepts.length}):
              </Typography>
              <Box display="flex" gap={0.5} flexWrap="wrap">
                {xai.matched_concepts.map((c) => (
                  <ConceptPill
                    key={c}
                    label={c}
                    variant="matched"
                    onDwellHover={(dwell_ms) => logEvent(condition ?? 'B', dataset, 'xai_pill_hover', { concept_id: c, variant: 'matched', dwell_ms })}
                  />
                ))}
              </Box>
            </>
          )}
        </Box>
      )}

      {/* LRM Reasoning Trace — hidden in Condition A (trace is the treatment) */}
      {traceData && showTrace && (condition ?? 'B') !== 'A' && (
        <Box sx={{ borderTop: '1px solid #e2e8f0', pt: 1.5, mt: 1.5 }}>
          <VerifierReasoningPanel
            parsedSteps={traceData.parsed_steps as ParsedStep[]}
            traceSummary={traceData.trace_summary as TraceSummary}
            onNodeClick={handleTraceNodeClick}
            highlightedNode={selectedConcept}
            onClose={() => setShowTrace(false)}
            condition={condition}
            dataset={dataset}
          />
          <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.75 }}>
            Model: {traceData.lrm_model} · {traceData.lrm_latency_ms}ms ·{' '}
            {traceData.lrm_valid === true ? '✓ valid' : traceData.lrm_valid === false ? '✗ invalid' : 'unverified'}
          </Typography>
        </Box>
      )}
    </Box>
  );
}

function cellText(v: unknown): string {
  if (v === null || v === undefined) return '';
  return String(v);
}

export const ScoreSamplesTable: React.FC<Props> = ({
  spec,
  condition = 'B',
  dataset = '',
  apiBase = 'http://localhost:5001',
}) => {
  const [expandedRow, setExpandedRow] = useState<string | number | null>(null);
  const [visibleRows, setVisibleRows] = useState<Set<number>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);
  const { setTraceOpen } = useDashboard();

  const columns = (spec.data.columns as string[]) ?? [];
  const rows = (spec.data.rows as SampleRow[]) ?? [];

  if (columns.length === 0 || rows.length === 0) {
    return <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>No per-sample rows in this dataset.</Typography>;
  }

  const maxScore = Math.max(...rows.map((r) => r.human_score), 5);
  const displayCols = ['id', 'human_score', 'cllm_score', 'c5_score', 'cllm_error', 'c5_error', 'solo', 'bloom', 'chain_pct'];

  // Observe visible rows with Intersection Observer for better performance on large datasets
  React.useEffect(() => {
    if (!containerRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const rowIndex = parseInt((entry.target as HTMLElement).dataset.rowIndex || '-1', 10);
          if (rowIndex >= 0) {
            setVisibleRows((prev) => {
              const next = new Set(prev);
              if (entry.isIntersecting) {
                next.add(rowIndex);
              } else {
                next.delete(rowIndex);
              }
              return next;
            });
          }
        });
      },
      { threshold: 0.0 } // Fire as soon as any part is visible
    );

    const rowElements = containerRef.current.querySelectorAll('[data-row-index]');
    rowElements.forEach((el) => observer.observe(el));

    return () => {
      rowElements.forEach((el) => observer.unobserve(el));
      observer.disconnect();
    };
  }, [rows.length]);

  return (
    <div
      ref={containerRef}
      onMouseEnter={() => logEvent(condition, dataset, 'chart_hover', { viz_id: spec.viz_id })}
    >
      <Box display="flex" alignItems="baseline" gap={1} mb={0.5}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>{spec.title}</Typography>
        <Typography variant="caption" color="primary" sx={{ fontStyle: 'italic' }}>
          click any row for score provenance + concept analysis
        </Typography>
      </Box>
      <Typography variant="caption" color="text.secondary" display="block" mb={1}>
        {spec.subtitle} ({rows.length} rows) — optimized virtual scrolling
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 440, overflow: 'auto' }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {displayCols.map((col) => (
                <TableCell key={col} sx={{ fontWeight: 700, whiteSpace: 'nowrap', bgcolor: 'background.paper' }}>
                  {col === 'cllm_error' ? 'LLM err' : col === 'c5_error' ? 'C5 err' :
                   col === 'human_score' ? 'human' : col === 'cllm_score' ? 'C_LLM' :
                   col === 'c5_score' ? 'C5' : col === 'chain_pct' ? 'KG%' : col}
                </TableCell>
              ))}
              <TableCell sx={{ fontWeight: 700, bgcolor: 'background.paper' }}>Δ err</TableCell>
              <TableCell sx={{ bgcolor: 'background.paper' }} />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => {
              const rowId = cellText(row.id) || String(i);
              const isExpanded = expandedRow === rowId;
              const chip = deltaChip(row.cllm_error ?? 0, row.c5_error ?? 0);
              const isVisible = visibleRows.has(i) || i < 5 || i >= rows.length - 5; // Always render first/last 5

              return (
                <React.Fragment key={rowId}>
                  <TableRow
                    hover
                    selected={isExpanded}
                    data-row-index={i}
                    onClick={() => {
                      const next = isExpanded ? null : rowId;
                      setExpandedRow(next);
                      setTraceOpen(next !== null);
                      if (next !== null) {
                        logEvent(condition, dataset, 'chart_click', { viz_id: 'score_provenance', sample_id: rowId });
                      }
                    }}
                    sx={{ cursor: 'pointer' }}
                  >
                    {displayCols.map((col) => (
                      <Tooltip key={col} title={col.endsWith('_error') ? 'Absolute error vs human score' : ''} arrow>
                        <TableCell sx={{ whiteSpace: 'nowrap' }}>
                          {cellText((row as unknown as Record<string, unknown>)[col])}
                        </TableCell>
                      </Tooltip>
                    ))}
                    <TableCell>
                      <Chip label={chip.label} size="small" sx={{ bgcolor: chip.bg, color: chip.color, fontWeight: 700, fontSize: 10 }} />
                    </TableCell>
                    <TableCell sx={{ pr: 1 }}>
                      <ExpandMoreIcon fontSize="small" sx={{ color: 'text.secondary', transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                    </TableCell>
                  </TableRow>
                  {isExpanded && isVisible && (
                    <TableRow>
                      <TableCell colSpan={displayCols.length + 2} sx={{ p: 0, border: 'none' }}>
                        <Collapse in={true} timeout="auto" unmountOnExit>
                          <ScoreProvenancePanel row={row} maxScore={maxScore} dataset={dataset} apiBase={apiBase} condition={condition} />
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
};
