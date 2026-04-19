/**
 * VerifierReasoningPanel — Stage 3b visual output.
 *
 * Renders the structured reasoning trace produced by the Python TraceParser
 * (Stage 3b) as an interactive list linked bidirectionally to the KG graph.
 *
 * Bidirectional brushing (Gemini VAST requirement):
 *   Click a reasoning step  → highlights the referenced KG nodes/edges
 *                             via DashboardContext.setHighlightedTraceNodes
 *   Click a KG node         → filters the step list to show only steps
 *                             that reference that node
 *
 * Classification colour coding:
 *   SUPPORTS    →  green  (#16a34a)
 *   CONTRADICTS →  red    (#dc2626)
 *   UNCERTAIN   →  amber  (#d97706)
 *
 * Each step also shows:
 *   - Confidence delta chip (e.g. "+0.10", "−0.15")
 *   - KG node pills (clickable to filter)
 *   - Conclusion badge (last cluster of steps)
 *
 * Props
 * -----
 * parsedSteps   : ParsedStep[]   — output of Python trace_parser.parse_trace()
 * traceSummary  : TraceSummary   — output of trace_parser.summarise_trace()
 * onNodeClick   : (nodeId) => void  — called when a node pill is clicked
 *                                     (parent should open ConceptKGPanel for that node)
 * highlightedNode : string | null   — node ID currently highlighted in the KG panel
 *                                     (filters steps on the receiving end)
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { logEvent } from '../../utils/studyLogger';
import {
  Alert,
  Box,
  Chip,
  Divider,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CancelOutlinedIcon from '@mui/icons-material/CancelOutlined';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import FlagIcon from '@mui/icons-material/Flag';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { useDashboard } from '../../contexts/DashboardContext';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ParsedStep {
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

interface Props {
  parsedSteps: ParsedStep[];
  traceSummary: TraceSummary;
  onNodeClick?: (nodeId: string) => void;
  highlightedNode?: string | null;
  onClose?: () => void;
  /** Study-mode props — when provided, trace_interact events are logged. */
  condition?: string;
  dataset?: string;
}

// ── Classification config ─────────────────────────────────────────────────────

const CLS_CONFIG = {
  SUPPORTS: {
    color:   '#16a34a',
    bgColor: '#f0fdf4',
    border:  '#bbf7d0',
    icon:    <CheckCircleOutlineIcon sx={{ fontSize: 16, color: '#16a34a' }} />,
    label:   'Supports',
  },
  CONTRADICTS: {
    color:   '#dc2626',
    bgColor: '#fef2f2',
    border:  '#fecaca',
    icon:    <CancelOutlinedIcon sx={{ fontSize: 16, color: '#dc2626' }} />,
    label:   'Contradicts',
  },
  UNCERTAIN: {
    color:   '#d97706',
    bgColor: '#fffbeb',
    border:  '#fde68a',
    icon:    <HelpOutlineIcon sx={{ fontSize: 16, color: '#d97706' }} />,
    label:   'Uncertain',
  },
} as const;

// ── Sub-components ────────────────────────────────────────────────────────────

function DeltaChip({ delta }: { delta: number }) {
  const positive = delta > 0;
  const zero     = delta === 0;
  const label    = zero ? '±0.00' : `${positive ? '+' : ''}${delta.toFixed(2)}`;
  return (
    <Chip
      label={label}
      size="small"
      sx={{
        fontSize: 10,
        height: 18,
        fontFamily: 'monospace',
        fontWeight: 700,
        bgcolor: zero ? '#f3f4f6' : positive ? '#dcfce7' : '#fee2e2',
        color:   zero ? '#6b7280' : positive ? '#15803d' : '#b91c1c',
        border: 'none',
      }}
    />
  );
}

function NodePill({
  nodeId,
  active,
  onClick,
}: {
  nodeId: string;
  active: boolean;
  onClick: (id: string) => void;
}) {
  const label = nodeId.replace(/_/g, ' ');
  return (
    <Chip
      label={label}
      size="small"
      onClick={() => onClick(nodeId)}
      sx={{
        fontSize: 10,
        height: 18,
        cursor: 'pointer',
        bgcolor: active ? '#dbeafe' : '#f1f5f9',
        color:   active ? '#1d4ed8' : '#475569',
        border: active ? '1px solid #93c5fd' : '1px solid #e2e8f0',
        fontWeight: active ? 700 : 400,
        '&:hover': { bgcolor: '#dbeafe', color: '#1d4ed8' },
      }}
    />
  );
}

function StepCard({
  step,
  isSelected,
  isFiltered,
  onSelect,
  onNodeClick,
}: {
  step: ParsedStep;
  isSelected: boolean;
  isFiltered: boolean;   // dimmed because highlightedNode filter is active and this step doesn't match
  onSelect:   (id: number) => void;
  onNodeClick: (nodeId: string) => void;
}) {
  const cfg = CLS_CONFIG[step.classification];

  return (
    <Paper
      elevation={isSelected ? 3 : 0}
      onClick={() => onSelect(step.step_id)}
      sx={{
        p: 1.25,
        mb: 0.75,
        cursor: 'pointer',
        border: `1px solid`,
        borderColor: isSelected ? cfg.color : cfg.border,
        bgcolor: isSelected ? cfg.bgColor : isFiltered ? '#f9fafb' : cfg.bgColor,
        opacity: isFiltered ? 0.45 : 1,
        transition: 'all 0.15s ease',
        '&:hover': { borderColor: cfg.color, opacity: 1, boxShadow: 2 },
      }}
    >
      {/* Header row */}
      <Box display="flex" alignItems="center" gap={0.75} mb={0.5}>
        <Tooltip title={cfg.label} placement="top" arrow>
          {cfg.icon}
        </Tooltip>
        <Typography variant="caption" sx={{ fontWeight: 700, color: cfg.color, fontSize: 10 }}>
          {cfg.label.toUpperCase()}
        </Typography>
        <DeltaChip delta={step.confidence_delta} />
        {step.is_conclusion && (
          <Tooltip title="Conclusion step" placement="top" arrow>
            <FlagIcon sx={{ fontSize: 13, color: '#7c3aed', ml: 0.25 }} />
          </Tooltip>
        )}
        <Typography variant="caption" color="text.disabled" sx={{ ml: 'auto', fontSize: 9 }}>
          #{step.step_id}
        </Typography>
      </Box>

      {/* Step text */}
      <Typography variant="body2" sx={{ fontSize: 12, lineHeight: 1.5, color: '#1e293b', mb: 0.75 }}>
        {step.text}
      </Typography>

      {/* KG node pills */}
      {step.kg_nodes.length > 0 && (
        <Box display="flex" flexWrap="wrap" gap={0.5} mt={0.25}>
          {step.kg_nodes.map((nodeId) => (
            <NodePill
              key={nodeId}
              nodeId={nodeId}
              active={isSelected}
              onClick={onNodeClick}
            />
          ))}
        </Box>
      )}
    </Paper>
  );
}

// ── Topological gap indicator ─────────────────────────────────────────────────
//
// Implements the edge-traversal element of the TRM formal definition:
//   "TRM evaluates topological continuity by measuring whether sequential steps
//    (sᵢ, sᵢ₊₁) map to connected subgraphs, exposing structural leaps."
//
// A "gap" occurs when step i and step i+1 share no KG nodes AND the edge
// types referenced by step i are not present in step i+1 — meaning the
// reasoning jumped to a disconnected region of the knowledge graph.

function hasTopologicalGap(stepA: ParsedStep, stepB: ParsedStep): boolean {
  if (stepA.kg_nodes.length === 0 || stepB.kg_nodes.length === 0) return false;
  // Node-only adjacency (locked v10/Gemini): two steps are topologically adjacent
  // iff their KG node sets intersect. Edge-type overlap is NOT sufficient — sharing
  // a relation type (e.g. both invoke HAS_PART) across disconnected subgraphs does
  // not constitute conceptual continuity. Simpler to defend formally; stricter.
  const nodesA = new Set(stepA.kg_nodes);
  return !stepB.kg_nodes.some(n => nodesA.has(n));  // gap iff no shared concept node
}

function TopologicalGapBadge({ stepA, stepB }: { stepA: ParsedStep; stepB: ParsedStep }) {
  return (
    <Tooltip
      title={
        `Structural leap: step #${stepA.step_id} references [${stepA.kg_nodes.map(n => n.replace(/_/g,' ')).join(', ')}] ` +
        `but step #${stepB.step_id} jumps to [${stepB.kg_nodes.map(n => n.replace(/_/g,' ')).join(', ')}] ` +
        `with no shared KG node or edge type — incomplete explanation: an intermediate concept was skipped.`
      }
      placement="right"
      arrow
    >
      <Box
        display="flex"
        alignItems="center"
        gap={0.5}
        sx={{
          my: 0.25,
          ml: 1,
          px: 1,
          py: 0.25,
          borderRadius: 1,
          bgcolor: '#fffbeb',
          border: '1px dashed #fbbf24',
          width: 'fit-content',
          cursor: 'help',
        }}
      >
        <WarningAmberIcon sx={{ fontSize: 11, color: '#d97706' }} />
        <Typography variant="caption" sx={{ fontSize: 9, color: '#92400e', fontWeight: 600 }}>
          structural leap — disconnected KG region
        </Typography>
      </Box>
    </Tooltip>
  );
}

// ── Summary bar ───────────────────────────────────────────────────────────────

function SummaryBar({
  summary,
  gapCount,
  groundingDensity,
}: {
  summary: TraceSummary;
  gapCount: number;
  groundingDensity: number;
}) {
  const netPositive = summary.net_delta >= 0;
  return (
    <Box
      display="flex"
      alignItems="center"
      gap={1.5}
      px={1.5}
      py={0.75}
      sx={{ bgcolor: '#f8fafc', borderRadius: 1, border: '1px solid #e2e8f0', flexWrap: 'wrap' }}
    >
      <Typography variant="caption" sx={{ fontWeight: 700, color: '#374151', fontSize: 11 }}>
        {summary.total_steps} steps
      </Typography>
      <Box display="flex" alignItems="center" gap={0.5}>
        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#16a34a' }} />
        <Typography variant="caption" color="text.secondary">{summary.supports_count} supports</Typography>
      </Box>
      <Box display="flex" alignItems="center" gap={0.5}>
        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#dc2626' }} />
        <Typography variant="caption" color="text.secondary">{summary.contradicts_count} contradicts</Typography>
      </Box>
      <Box display="flex" alignItems="center" gap={0.5}>
        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#d97706' }} />
        <Typography variant="caption" color="text.secondary">{summary.uncertain_count} uncertain</Typography>
      </Box>
      <Divider orientation="vertical" flexItem />
      <Tooltip
        title="Sum of all confidence deltas across parsed steps. Positive = net support for the student's chain."
        placement="top"
        arrow
      >
        <Typography
          variant="caption"
          sx={{
            fontFamily: 'monospace',
            fontWeight: 700,
            color: netPositive ? '#15803d' : '#b91c1c',
            cursor: 'help',
          }}
        >
          Δ {netPositive ? '+' : ''}{summary.net_delta.toFixed(2)}
        </Typography>
      </Tooltip>
      <Divider orientation="vertical" flexItem />
      <Tooltip
        title={`Grounding Density: ${(groundingDensity * 100).toFixed(0)}% of steps are anchored to at least one KG concept node. Low density means the LRM reasoned without naming domain concepts explicitly.`}
        placement="top"
        arrow
      >
        <Typography
          variant="caption"
          sx={{
            fontSize: 10,
            fontFamily: 'monospace',
            color: groundingDensity >= 0.5 ? '#15803d' : groundingDensity >= 0.25 ? '#b45309' : '#b91c1c',
            cursor: 'help',
          }}
        >
          {(groundingDensity * 100).toFixed(0)}% grounded
        </Typography>
      </Tooltip>
      {gapCount > 0 && (
        <>
          <Divider orientation="vertical" flexItem />
          <Tooltip
            title="Structural leaps: consecutive reasoning steps with no shared KG concept node, indicating the LRM skipped an intermediate concept. These are incomplete explanations — not necessarily factual errors."
            placement="top"
            arrow
          >
            <Box display="flex" alignItems="center" gap={0.4} sx={{ cursor: 'help' }}>
              <WarningAmberIcon sx={{ fontSize: 11, color: '#d97706' }} />
              <Typography variant="caption" sx={{ fontSize: 10, color: '#92400e', fontWeight: 600 }}>
                {gapCount} leap{gapCount !== 1 ? 's' : ''}
              </Typography>
            </Box>
          </Tooltip>
        </>
      )}
    </Box>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export const VerifierReasoningPanel: React.FC<Props> = ({
  parsedSteps,
  traceSummary,
  onNodeClick,
  highlightedNode,
  onClose,
  condition = 'B',
  dataset = '',
}) => {
  const [selectedStepId, setSelectedStepId] = useState<number | null>(null);
  const { pushContradicts, setTraceGapCount, setGroundingDensity } = useDashboard();

  // Count structural leaps (node-only adjacency, locked v10).
  const topologicalGapCount = useMemo(() => {
    let count = 0;
    for (let i = 1; i < parsedSteps.length; i++) {
      if (hasTopologicalGap(parsedSteps[i - 1], parsedSteps[i])) count++;
    }
    return count;
  }, [parsedSteps]);

  // Grounding Density: fraction of steps with ≥1 kg_node populated ∈ [0, 1].
  // Measures how well the LRM anchored its reasoning to domain KG concepts.
  const groundingDensity = useMemo(() => {
    if (parsedSteps.length === 0) return 0;
    const grounded = parsedSteps.filter(s => s.kg_nodes.length > 0).length;
    return grounded / parsedSteps.length;
  }, [parsedSteps]);

  // Publish both metrics to DashboardContext for rubric_edit payload logging.
  useEffect(() => {
    setTraceGapCount(topologicalGapCount);
  }, [topologicalGapCount, setTraceGapCount]);

  useEffect(() => {
    setGroundingDensity(groundingDensity);
  }, [groundingDensity, setGroundingDensity]);

  // When a step is clicked: toggle selection + notify parent to highlight KG nodes.
  // If the step is a CONTRADICTS step, push it onto the rolling 60-second window in
  // DashboardContext so RubricEditorPanel can compute multi-window causal attribution.
  const handleSelectStep = useCallback(
    (stepId: number) => {
      const nextId = selectedStepId === stepId ? null : stepId;
      setSelectedStepId(nextId);

      if (nextId !== null) {
        const step = parsedSteps.find((s) => s.step_id === nextId);
        if (step) {
          // Log ALL step clicks (SUPPORTS/CONTRADICTS/UNCERTAIN) for engagement analysis.
          // analyze_study_logs.py counts trace_interactions and contradicts_interactions
          // from these events; without them both metrics are always 0.
          logEvent(condition, dataset, 'trace_interact', {
            classification: step.classification,
            node_id: step.kg_nodes[0] ?? null,
            step_id: step.step_id,
          });

          // Causal proximity tracking: append CONTRADICTS interaction to rolling window.
          // Only push when kg_nodes is non-empty — synthetic IDs like step_3 are
          // unmatchable in conceptAliases.matchesContradictsNode and would inflate
          // the rolling window with false entries (identified in code review v1).
          if (step.classification === 'CONTRADICTS' && step.kg_nodes.length > 0) {
            pushContradicts(step.kg_nodes[0]);
          }
          // KG node brushing
          if (onNodeClick && step.kg_nodes.length > 0) {
            onNodeClick(step.kg_nodes[0]);
          }
        }
      }
    },
    [selectedStepId, parsedSteps, onNodeClick, pushContradicts, condition, dataset],
  );

  const handleNodePillClick = useCallback(
    (nodeId: string) => {
      onNodeClick?.(nodeId);
      // Node pill clicks on CONTRADICTS steps also count as causal interactions
      const step = parsedSteps.find(s => s.kg_nodes.includes(nodeId) && s.classification === 'CONTRADICTS');
      if (step) {
        logEvent(condition, dataset, 'trace_interact', {
          classification: 'CONTRADICTS',
          node_id: nodeId,
          step_id: step.step_id,
        });
        pushContradicts(nodeId);
      }
    },
    [onNodeClick, parsedSteps, pushContradicts, condition, dataset],
  );

  if (parsedSteps.length === 0) {
    return (
      <Alert severity="info" sx={{ fontSize: 12 }}>
        No reasoning trace available. Run the LRM verifier (Stage 3a) to generate trace data.
      </Alert>
    );
  }

  // When a KG node is highlighted externally (e.g. user clicked in ConceptKGPanel),
  // dim steps that do NOT reference that node (bidirectional brushing receiving end).
  const hasNodeFilter = Boolean(highlightedNode);
  const filteredStepIds = hasNodeFilter
    ? new Set(parsedSteps.filter((s) => s.kg_nodes.includes(highlightedNode!)).map((s) => s.step_id))
    : null;

  return (
    <Box>
      {/* Header */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, fontSize: 14 }}>
            LRM Reasoning Trace
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Click a step to highlight KG nodes · click a node pill to open KG view
            {hasNodeFilter && ` · filtered by node: ${highlightedNode!.replace(/_/g, ' ')}`}
          </Typography>
        </Box>
        {onClose && (
          <IconButton size="small" onClick={onClose}>
            <CloseIcon fontSize="small" />
          </IconButton>
        )}
      </Box>

      {/* Summary bar */}
      <SummaryBar summary={traceSummary} gapCount={topologicalGapCount} groundingDensity={groundingDensity} />

      {/* Zero-grounding degeneracy banner — shown when ALL steps have kg_nodes: [].
          This is the common case for DeepSeek-R1 traces (97.7% of DigiKlausur answers).
          Topological gap detection cannot operate without KG node anchors; the banner
          warns the educator that structural leap indicators are suppressed, not absent.
          Implemented per AGENT_EVALUATION_GUIDE §2 "Zero-Grounding Graceful Rendering". */}
      {groundingDensity === 0 && parsedSteps.length > 0 && (
        <Alert
          severity="warning"
          icon={<WarningAmberIcon fontSize="inherit" />}
          sx={{ mt: 1, fontSize: 11, '& .MuiAlert-message': { lineHeight: 1.5 } }}
        >
          <strong>No Domain Grounding</strong> — All {parsedSteps.length} reasoning step
          {parsedSteps.length !== 1 ? 's' : ''} lack KG concept anchors (grounding density = 0%).
          Structural leap detection is disabled for this trace. This is a known degeneracy
          pattern in DeepSeek-R1 traces; use the SUPPORTS / CONTRADICTS chips and the score
          delta to audit this answer.
        </Alert>
      )}

      {/* Conclusion callout */}
      {traceSummary.conclusion_text && (
        <Box
          mt={1}
          p={1}
          sx={{
            bgcolor: '#faf5ff',
            border: '1px solid #e9d5ff',
            borderRadius: 1,
            display: 'flex',
            gap: 0.75,
            alignItems: 'flex-start',
          }}
        >
          <FlagIcon sx={{ fontSize: 14, color: '#7c3aed', mt: 0.15, flexShrink: 0 }} />
          <Typography variant="caption" sx={{ color: '#4c1d95', lineHeight: 1.5, fontSize: 11 }}>
            <strong>Conclusion: </strong>{traceSummary.conclusion_text}
          </Typography>
        </Box>
      )}

      {/* Steps list — with topological gap indicators between disconnected steps */}
      <Stack mt={1.25} spacing={0}>
        {parsedSteps.map((step, idx) => {
          const prevStep = parsedSteps[idx - 1];
          const showGap = prevStep ? hasTopologicalGap(prevStep, step) : false;
          return (
            <React.Fragment key={step.step_id}>
              {showGap && <TopologicalGapBadge stepA={prevStep} stepB={step} />}
              <StepCard
                step={step}
                isSelected={selectedStepId === step.step_id}
                isFiltered={filteredStepIds !== null && !filteredStepIds.has(step.step_id)}
                onSelect={handleSelectStep}
                onNodeClick={handleNodePillClick}
              />
            </React.Fragment>
          );
        })}
      </Stack>

      {/* Edge types referenced */}
      {traceSummary.edges_referenced.length > 0 && (
        <Box mt={1} display="flex" flexWrap="wrap" gap={0.5} alignItems="center">
          <Typography variant="caption" color="text.disabled" sx={{ mr: 0.25 }}>
            Relationships evaluated:
          </Typography>
          {traceSummary.edges_referenced.map((edge) => (
            <Chip
              key={edge}
              label={edge.replace(/_/g, ' ')}
              size="small"
              variant="outlined"
              sx={{ fontSize: 9, height: 16, color: '#64748b', borderColor: '#e2e8f0' }}
            />
          ))}
        </Box>
      )}
    </Box>
  );
};

export default VerifierReasoningPanel;
