/**
 * RubricEditorPanel — User study rubric feedback component.
 *
 * Condition A (no trace context):
 *   - Shows rubric concept list only (no CONTRADICTS strip, no LRM-flagged chips).
 *   - Allows edits; comparison data for what educators change without trace context.
 *
 * Condition B (trace context — post-task):
 *   - CONTRADICTS chip strip: shows every concept the LRM flagged across all traces.
 *   - Each chip is Click-to-Add (eliminates lexical ambiguity; logs canonical node ID).
 *   - Warning banner highlights flagged concepts missing from the rubric.
 *   - Rubric concept list with 4 action buttons each.
 *
 * Causal attribution (every rubric_edit event):
 *   Multi-window: within_15s / within_30s / within_60s (all pre-registered).
 *   Semantic:     exact ID match + Levenshtein fuzzy match + domain alias dictionary.
 *   Panel timing: panel_focus_ms + panel_focus_before_trace.
 *   Source:       'click_to_add' (chip click) vs 'manual' (button click).
 *
 * These fields enable analyze_study_logs.py to compute causal_attribution_rate,
 * concept_alignment_rate, and semantic_alignment_rate without researcher DoF.
 */

import React, { useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';

import { useDashboard } from '../../contexts/DashboardContext';
import { logEvent, RubricEditPayload, StudyCondition } from '../../utils/studyLogger';
import { matchesContradictsNode } from '../../utils/conceptAliases';
import { VisualizationSpec } from '../../common/visualization.types';

// ── Types ─────────────────────────────────────────────────────────────────────

type EditType = 'add' | 'remove' | 'increase_weight' | 'decrease_weight';

interface RubricEdit {
  concept_id:  string;
  edit_type:   EditType;
  timestamp_ms: number;
}

interface RubricEditorPanelProps {
  condition: StudyCondition;
  dataset:   string;
  /** All VisualizationSpecs for the selected dataset — used to extract KG nodes. */
  specs: VisualizationSpec[];
  /**
   * Accumulated set of CONTRADICTS node IDs seen across all trace interactions
   * this session. Passed down from InstructorDashboard.
   * Empty array for Condition A (no trace context shown).
   */
  sessionContradictsNodes: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Extract a flat concept ID list from the dataset's concept_frequency spec.
 *  concept_frequency bars have the shape { concept: string (raw id), label: string (display), ... }.
 *  rubric_size = concepts.length is emitted in every rubric_edit event so that
 *  analyze_study_logs.py can use the true N for the hypergeometric null model (H2).
 */
function extractConceptsFromSpecs(specs: VisualizationSpec[]): string[] {
  const concepts = new Set<string>();
  for (const spec of specs) {
    if (spec.viz_id === 'concept_frequency') {
      // data.bars is produced by visualization.service.ts buildConceptFrequency()
      const bars = (spec.data as any)?.bars ?? [];
      for (const bar of bars) {
        if (bar?.concept) concepts.add(String(bar.concept));
      }
    }
    if (spec.insights) {
      for (const insight of spec.insights) {
        const matches = insight.match(/\b[A-Z][a-z]+(?:_[A-Z][a-z]+)+\b/g) ?? [];
        for (const m of matches) concepts.add(m);
      }
    }
  }
  return Array.from(concepts).sort();
}

function editLabel(type: EditType): string {
  switch (type) {
    case 'add':             return 'Add to rubric';
    case 'remove':          return 'Remove from rubric';
    case 'increase_weight': return 'Increase weight';
    case 'decrease_weight': return 'Decrease weight';
  }
}

function editColor(type: EditType): 'success' | 'error' | 'warning' | 'info' {
  switch (type) {
    case 'add':             return 'success';
    case 'remove':          return 'error';
    case 'increase_weight': return 'warning';
    case 'decrease_weight': return 'info';
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export function RubricEditorPanel({
  condition,
  dataset,
  specs,
  sessionContradictsNodes,
}: RubricEditorPanelProps) {
  // Rolling 60-second window, gap count, and grounding density from DashboardContext.
  const { recentContradicts, lastTraceGapCount, lastGroundingDensity } = useDashboard();

  const [edits, setEdits]       = useState<RubricEdit[]>([]);
  const [submitted, setSubmitted] = useState(false);

  // Capture mount timestamp and whether the panel opened before any trace interaction.
  const panelMountMs         = useRef(Date.now());
  const panelBeforeTrace     = useRef<boolean>(sessionContradictsNodes.length === 0);

  const concepts = useMemo(() => extractConceptsFromSpecs(specs), [specs]);

  // Concepts the LRM flagged but not yet in the rubric (candidates for "add" action).
  const contradictsNotInRubric = useMemo(
    () => sessionContradictsNodes.filter(n => !concepts.includes(n)),
    [sessionContradictsNodes, concepts],
  );

  const editedIds = new Set(edits.map(e => e.concept_id));

  // ── Core edit handler ──────────────────────────────────────────────────────
  //
  // Called by both Click-to-Add chip clicks and manual button clicks.
  // Computes multi-window attribution atomically at the moment of the edit.

  function handleEdit(
    conceptId:    string,
    conceptLabel: string,
    editType:     EditType,
    source:       'click_to_add' | 'manual' = 'manual',
  ) {
    const now = Date.now();

    // ── Multi-window attribution from rolling recentContradicts ──────────────
    // recentContradicts already pruned to 60 s in the reducer; filter tighter here.
    const w60 = recentContradicts.filter(e => now - e.timestamp_ms <= 60_000);
    const w30 = w60.filter(e => now - e.timestamp_ms <= 30_000);
    const w15 = w30.filter(e => now - e.timestamp_ms <= 15_000);

    const mostRecent = w60.length > 0 ? w60[w60.length - 1] : null;

    // ── Semantic alias matching ──────────────────────────────────────────────
    const { matched: semanticMatch, bestMatch, score } = matchesContradictsNode(
      conceptId,
      sessionContradictsNodes,
    );

    const payload: RubricEditPayload = {
      edit_type:    editType,
      concept_id:   conceptId,
      concept_label: conceptLabel,
      // Multi-window
      within_15s: w15.length > 0,
      within_30s: w30.length > 0,
      within_60s: w60.length > 0,
      time_since_last_contradicts_ms: mostRecent ? now - mostRecent.timestamp_ms : null,
      source_contradicts_nodes_60s: [...new Set(w60.map(e => e.nodeId))],
      // Concept alignment
      concept_in_contradicts_exact:    sessionContradictsNodes.includes(conceptId),
      concept_in_contradicts_semantic: semanticMatch,
      semantic_match_score:            score > 0 ? score : null,
      semantic_match_node:             bestMatch,
      session_contradicts_nodes:       sessionContradictsNodes,
      // Panel timing
      panel_mount_timestamp_ms: panelMountMs.current,
      panel_focus_before_trace: panelBeforeTrace.current,
      // Source
      interaction_source: source,
      // Topological gap & grounding density moderators
      trace_gap_count:   lastTraceGapCount,
      grounding_density: lastGroundingDensity,
      // True rubric size for hypergeometric null model (H2 — analyze_study_logs.py)
      rubric_size: concepts.length,
    };

    logEvent(condition, dataset, 'rubric_edit', payload as unknown as Record<string, unknown>);

    setEdits(prev => {
      const without = prev.filter(e => e.concept_id !== conceptId);
      return [...without, { concept_id: conceptId, edit_type: editType, timestamp_ms: now }];
    });
  }

  function handleSubmitEdits() {
    logEvent(condition, dataset, 'task_submit', {
      event_subtype:      'rubric_review',
      total_edits:        edits.length,
      edits_summary:      edits,
      session_elapsed_ms: Date.now() - panelMountMs.current,
    });
    setSubmitted(true);
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (submitted) {
    return (
      <Alert severity="success" icon={<CheckCircleOutlineIcon />} sx={{ mt: 2 }}>
        Rubric feedback submitted — {edits.length} edit(s) recorded. Thank you!
      </Alert>
    );
  }

  const hasTraceContext = condition === 'B' && sessionContradictsNodes.length > 0;

  return (
    <Paper variant="outlined" sx={{ p: 3, mt: 3 }}>
      <Typography variant="h6" gutterBottom>
        Rubric Review{condition === 'A' && ' (no trace context)'}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {condition === 'B'
          ? 'Based on the grading traces above, would you adjust the rubric for this dataset? Flag each concept below. Your edits are recorded with the trace context you were viewing.'
          : 'Would you adjust the rubric for this dataset based on your domain expertise? Flag each concept below.'}
      </Typography>

      {/* CONTRADICTS chip strip — Condition B only (Click-to-Add) ─────────── */}
      {hasTraceContext && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Concepts the LRM flagged as CONTRADICTS in student traces:
          </Typography>
          <Stack direction="row" flexWrap="wrap" gap={1}>
            {sessionContradictsNodes.map(node => {
              const alreadyAdded = editedIds.has(node);
              return (
                <Tooltip
                  key={node}
                  title={alreadyAdded ? 'Already added to your rubric edits' : 'Click to add this concept to your rubric feedback'}
                  placement="top"
                  arrow
                >
                  <Chip
                    label={node.replace(/_/g, ' ')}
                    size="small"
                    color={alreadyAdded ? 'default' : 'error'}
                    variant={alreadyAdded ? 'filled' : 'outlined'}
                    icon={alreadyAdded ? <CheckCircleOutlineIcon /> : <AddCircleOutlineIcon />}
                    onClick={alreadyAdded ? undefined : () => handleEdit(node, node, 'add', 'click_to_add')}
                    sx={{
                      cursor: alreadyAdded ? 'default' : 'pointer',
                      opacity: alreadyAdded ? 0.60 : 1,
                      fontWeight: alreadyAdded ? 400 : 700,
                      '& .MuiChip-icon': { fontSize: 14 },
                      // Pulse 3 times on mount to signal clickability, then stops.
                      // Skipped for already-added chips (no action needed).
                      ...(alreadyAdded ? {} : {
                        animation: 'contradicts-pulse 1.6s ease-out 3',
                        '@keyframes contradicts-pulse': {
                          '0%':   { boxShadow: '0 0 0 0 rgba(220,38,38,0.45)' },
                          '60%':  { boxShadow: '0 0 0 7px rgba(220,38,38,0)' },
                          '100%': { boxShadow: '0 0 0 0 rgba(220,38,38,0)' },
                        },
                      }),
                    }}
                  />
                </Tooltip>
              );
            })}
          </Stack>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>
            Click a chip to add it directly — no typing needed.
          </Typography>

          {contradictsNotInRubric.length > 0 && (
            <Alert severity="warning" sx={{ mt: 1 }} variant="outlined">
              {contradictsNotInRubric.length} LRM-flagged concept(s) not in the current rubric:{' '}
              {contradictsNotInRubric.map(n => n.replace(/_/g, ' ')).join(', ')}.
              Consider adding them above.
            </Alert>
          )}
        </Box>
      )}

      <Divider sx={{ mb: 2 }} />

      {/* Rubric concept list ────────────────────────────────────────────────── */}
      <Typography variant="subtitle2" gutterBottom>
        Current rubric concepts ({concepts.length}):
      </Typography>

      {concepts.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          No rubric concepts extracted from the current dataset specs.
        </Typography>
      )}

      <Stack spacing={1} sx={{ mb: 3 }}>
        {concepts.map(concept => {
          const existingEdit = edits.find(e => e.concept_id === concept);
          const isLrmFlagged = hasTraceContext && sessionContradictsNodes.includes(concept);

          return (
            <Box
              key={concept}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1,
                borderRadius: 1,
                bgcolor: existingEdit ? 'action.selected' : 'transparent',
                border: '1px solid',
                borderColor: existingEdit ? 'primary.main' : 'divider',
              }}
            >
              <Typography
                variant="body2"
                sx={{ flex: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}
              >
                {concept.replace(/_/g, ' ')}
                {isLrmFlagged && (
                  <Chip
                    label="LRM flagged"
                    size="small"
                    color="error"
                    sx={{ ml: 1, height: 16, fontSize: '0.65rem' }}
                  />
                )}
              </Typography>

              {existingEdit ? (
                <Chip
                  label={editLabel(existingEdit.edit_type)}
                  size="small"
                  color={editColor(existingEdit.edit_type)}
                  onDelete={() => setEdits(prev => prev.filter(e => e.concept_id !== concept))}
                />
              ) : (
                <Stack direction="row" spacing={0.5}>
                  <Tooltip title="Remove — concept is out-of-scope for this course">
                    <Button
                      size="small"
                      color="error"
                      variant="outlined"
                      startIcon={<RemoveCircleOutlineIcon />}
                      onClick={() => handleEdit(concept, concept, 'remove')}
                      sx={{ minWidth: 0, px: 1 }}
                    >
                      Remove
                    </Button>
                  </Tooltip>
                  <Tooltip title="Increase weight — under-emphasised in the rubric">
                    <Button
                      size="small"
                      color="warning"
                      variant="outlined"
                      startIcon={<ArrowUpwardIcon />}
                      onClick={() => handleEdit(concept, concept, 'increase_weight')}
                      sx={{ minWidth: 0, px: 1 }}
                    >
                      ↑ Weight
                    </Button>
                  </Tooltip>
                  <Tooltip title="Decrease weight — over-emphasised in the rubric">
                    <Button
                      size="small"
                      color="info"
                      variant="outlined"
                      startIcon={<ArrowDownwardIcon />}
                      onClick={() => handleEdit(concept, concept, 'decrease_weight')}
                      sx={{ minWidth: 0, px: 1 }}
                    >
                      ↓ Weight
                    </Button>
                  </Tooltip>
                </Stack>
              )}
            </Box>
          );
        })}
      </Stack>

      {/* Add LRM-flagged concepts not yet in rubric (manual add buttons) ───── */}
      {hasTraceContext && contradictsNotInRubric.filter(n => !editedIds.has(n)).length > 0 && (
        <>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            Add LRM-flagged concepts to the rubric:
          </Typography>
          <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mb: 2 }}>
            {contradictsNotInRubric.filter(n => !editedIds.has(n)).map(node => (
              <Button
                key={node}
                size="small"
                color="success"
                variant="outlined"
                startIcon={<AddCircleOutlineIcon />}
                onClick={() => handleEdit(node, node, 'add', 'manual')}
              >
                Add: {node.replace(/_/g, ' ')}
              </Button>
            ))}
          </Stack>
        </>
      )}

      {/* Edit summary ───────────────────────────────────────────────────────── */}
      {edits.length > 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {edits.length} edit(s) pending —{' '}
          {edits.map(e => `${editLabel(e.edit_type)}: ${e.concept_id.replace(/_/g, ' ')}`).join('; ')}
        </Alert>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleSubmitEdits}
        disabled={edits.length === 0}
      >
        Submit Rubric Feedback ({edits.length} edit{edits.length !== 1 ? 's' : ''})
      </Button>
    </Paper>
  );
}
