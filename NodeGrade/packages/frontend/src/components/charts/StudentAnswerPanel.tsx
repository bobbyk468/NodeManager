/**
 * StudentAnswerPanel — Master-Detail layout (Gemini recommendation).
 *
 * LEFT: scrollable compact list of student items, sorted by severity.
 *       Each item shows severity chip, student ID, score badges, 1-line answer preview.
 *       Clicking selects the student → updates DashboardContext (KG overlay).
 *
 * RIGHT: fixed detail pane showing full student answer, KG coverage metadata,
 *        SOLO/Bloom levels. No accordion jumping.
 *
 * Filtered by:
 *   - selectedSeverity from heatmap cell click (default: show that severity first)
 *   - selectedQuartileIndex from radar click (filter by score quartile)
 */

import CloseIcon from '@mui/icons-material/Close';
import FilterListIcon from '@mui/icons-material/FilterList';
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material';
import React, { useEffect, useMemo, useRef, useState } from 'react';

import { ConceptAnswersResponse, ConceptStudentAnswer, SampleXAIData } from '../../common/visualization.types';
import { useDashboard } from '../../contexts/DashboardContext';
import { getBenchmarkCase } from '../../utils/benchmarkSeeds';
import { AnswerDwellPayload, getBeaconCaptureMethod, logBeacon, logEvent } from '../../utils/studyLogger';

/**
 * FNV-1a 64-bit hash of a UTF-16 string (via BigInt).
 *
 * FERPA compliance: raw student answer text is NEVER included in event logs.
 * Only this deterministic, non-reversible hash is transmitted. Analysts can
 * verify that the same answer was shown consistently across participants by
 * comparing hashes, without ever seeing the student text.
 *
 * Algorithm: FNV-1a (Fowler–Noll–Vo variant 1a), 64-bit.
 * Upgraded from 32-bit: at 32 bits, Birthday-paradox collision probability
 * reaches ~50% at ~77k items — non-negligible across a full study dataset.
 * 64-bit reduces collision probability to negligible (~1 in 10^14 at N=10k).
 */
function fnv1a(text: string): string {
  let hash = BigInt('0xcbf29ce484222325');
  const prime = BigInt('0x00000100000001b3');
  const mask64 = (BigInt(1) << BigInt(64)) - BigInt(1);
  for (let i = 0; i < text.length; i++) {
    hash ^= BigInt(text.charCodeAt(i));
    hash = (hash * prime) & mask64;
  }
  return hash.toString(16).padStart(16, '0');
}

interface Props {
  dataset: string;
  conceptId: string;
  defaultSeverity?: string | null;  // severity of the cell that was clicked
  apiBase: string;
  onClose: () => void;
  onShowKG?: () => void;
  // Study-mode props — when provided, dwell-time events are logged
  studyCondition?: string;       // 'A' | 'B'; if omitted, logging is skipped
  tracePanelOpen?: boolean;      // is the VerifierReasoningPanel currently visible?
  kgPanelOpen?: boolean;         // is the ConceptKGPanel currently visible?
}

const SEVERITY_COLOR: Record<string, string> = {
  matched: '#16a34a',
  critical: '#dc2626',
  moderate: '#ea580c',
  minor: '#9ca3af',
};

const SEVERITY_LABEL: Record<string, string> = {
  matched: 'Covered',
  critical: 'Critical miss',
  moderate: 'Moderate miss',
  minor: 'Minor miss',
};

// Quartile score boundaries matching generate_dashboard_extras.py logic
function scoreToQuartile(score: number, allScores: number[]): number {
  const sorted = [...allScores].sort((a, b) => a - b);
  const n = sorted.length;
  const boundaries = [sorted[Math.floor(n / 4)], sorted[Math.floor(n / 2)], sorted[Math.floor((3 * n) / 4)]];
  if (score < boundaries[0]) return 0;
  if (score < boundaries[1]) return 1;
  if (score < boundaries[2]) return 2;
  return 3;
}

function ScoreDot({ value, color, label }: { value: number; color: string; label: string }) {
  return (
    <Tooltip title={`${label}: ${value.toFixed(1)}`} arrow>
      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="caption" sx={{ fontSize: 9, color: 'text.secondary', display: 'block', lineHeight: 1 }}>
          {label}
        </Typography>
        <Typography variant="caption" sx={{ fontWeight: 700, color, fontSize: 11 }}>
          {value.toFixed(1)}
        </Typography>
      </Box>
    </Tooltip>
  );
}

// Neutral colour used for Condition A rows — no AI-derived severity signal.
const CONDITION_A_ROW_COLOR = '#6b7280';

function StudentListItem({
  answer,
  isSelected,
  isConditionA,
  onClick,
}: {
  answer: ConceptStudentAnswer;
  isSelected: boolean;
  isConditionA: boolean;
  onClick: () => void;
}) {
  // Condition A: suppress severity colour (KG-derived signal) — use neutral grey.
  // Condition B: full severity colour (red/orange/grey/green) for prioritisation.
  const color = isConditionA ? CONDITION_A_ROW_COLOR : (SEVERITY_COLOR[answer.severity] ?? '#6b7280');
  return (
    <Box
      onClick={onClick}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        px: 1.5,
        py: 0.75,
        cursor: 'pointer',
        bgcolor: isSelected ? `${color}12` : 'transparent',
        borderLeft: isSelected ? `3px solid ${color}` : '3px solid transparent',
        '&:hover': { bgcolor: `${color}08` },
        transition: 'background-color 0.1s',
      }}
    >
      <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: color, flexShrink: 0 }} />
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block' }}>
          #{answer.id}
        </Typography>
        <Typography
          variant="caption"
          color="text.secondary"
          noWrap
          sx={{ fontSize: 10, display: 'block' }}
        >
          {answer.student_answer.slice(0, 55)}{answer.student_answer.length > 55 ? '…' : ''}
        </Typography>
      </Box>
      <Box display="flex" gap={0.5} flexShrink={0}>
        <ScoreDot value={answer.human_score} color="#374151" label="H" />
        <ScoreDot value={answer.c5_score} color="#16a34a" label="C5" />
      </Box>
    </Box>
  );
}

function StudentDetailPane({ answer, isConditionA }: { answer: ConceptStudentAnswer; isConditionA: boolean }) {
  // Condition A: suppress AI-derived severity label and colour-tinted answer box.
  // Condition B: full severity chip + colour coding for concept-gap diagnostics.
  const color = isConditionA ? CONDITION_A_ROW_COLOR : (SEVERITY_COLOR[answer.severity] ?? '#6b7280');
  const label = SEVERITY_LABEL[answer.severity] ?? answer.severity;
  return (
    <Box sx={{ p: 2, height: '100%', overflowY: 'auto' }}>
      <Box display="flex" alignItems="center" gap={1} mb={1.5}>
        {isConditionA
          ? <Chip label="Student answer" size="small" sx={{ bgcolor: '#f3f4f6', color: '#374151', fontWeight: 600 }} />
          : <Chip label={label} size="small" sx={{ bgcolor: `${color}22`, color, fontWeight: 700 }} />
        }
        <Typography variant="caption" color="text.secondary">Student #{answer.id}</Typography>
      </Box>

      {/* Score breakdown */}
      <Box display="flex" gap={2} mb={1.5}>
        {[
          { label: 'Human', value: answer.human_score, color: '#374151' },
          { label: 'C_LLM', value: answer.cllm_score, color: '#dc2626' },
          { label: 'ConceptGrade', value: answer.c5_score, color: '#16a34a' },
        ].map(({ label, value, color: c }) => (
          <Box key={label} textAlign="center">
            <Typography variant="caption" color="text.secondary" display="block">{label}</Typography>
            <Typography variant="body2" sx={{ fontWeight: 700, color: c }}>{value.toFixed(2)}</Typography>
          </Box>
        ))}
      </Box>

      <Divider sx={{ mb: 1.5 }} />

      {/* Question */}
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
        Question
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontStyle: 'italic', fontSize: 11 }}>
        {answer.question}
      </Typography>

      {/* Student answer */}
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
        Student answer
      </Typography>
      <Box sx={{ p: 1.5, bgcolor: isConditionA ? '#f8fafc' : `${color}0d`, borderRadius: 1, border: `1px solid ${isConditionA ? '#e2e8f0' : `${color}33`}`, mb: 1.5 }}>
        <Typography variant="body2" sx={{ lineHeight: 1.6, fontStyle: 'italic' }}>
          "{answer.student_answer}"
        </Typography>
      </Box>

      {/* Metadata chips */}
      <Box display="flex" gap={1} flexWrap="wrap">
        <Chip label={`SOLO: ${answer.solo || '—'}`} size="small" variant="outlined" />
        <Chip label={`Bloom: ${answer.bloom || '—'}`} size="small" variant="outlined" />
        <Chip label={`KG coverage: ${answer.chain_pct || '—'}`} size="small" variant="outlined" />
      </Box>
    </Box>
  );
}

export const StudentAnswerPanel: React.FC<Props> = ({
  dataset,
  conceptId,
  defaultSeverity,
  apiBase,
  onClose,
  onShowKG,
  studyCondition,
  tracePanelOpen = false,
  kgPanelOpen = false,
}) => {
  const { selectStudent, setStudentOverlayLoading, setStudentOverlayError, selectedStudentId, selectedQuartileIndex } = useDashboard();
  // Guards against applying a stale XAI fetch result when the user clicks rapidly
  const latestSelectedIdRef = useRef<string | number | null>(null);
  // Tracks the timestamp when the current answer was selected (for dwell-time computation).
  // Updated on every answer_view_start; read in the cleanup to compute answer_view_end.
  const answerViewStartRef = useRef<number | null>(null);

  const [data, setData] = useState<ConceptAnswersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>(defaultSeverity ?? 'all');

  // Reset severity filter when concept changes
  useEffect(() => {
    setSeverityFilter(defaultSeverity ?? 'all');
  }, [conceptId, defaultSeverity]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setData(null);
    selectStudent(null);
    fetch(`${apiBase}/api/visualization/datasets/${dataset}/concept/${conceptId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<ConceptAnswersResponse>;
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e: Error) => { setError(e.message); setLoading(false); });
  }, [dataset, conceptId, apiBase]); // eslint-disable-line react-hooks/exhaustive-deps

  // Compute all human scores for quartile mapping
  const allScores = useMemo(() => (data?.answers ?? []).map((a) => a.human_score), [data]);

  // Apply filters: severity + radar quartile
  const displayed = useMemo(() => {
    if (!data) return [];
    let list = data.answers;

    if (severityFilter !== 'all') {
      list = list.filter((a) =>
        severityFilter === 'matched' ? a.matched : a.severity === severityFilter,
      );
    }

    if (selectedQuartileIndex !== null && allScores.length > 0) {
      list = list.filter((a) => scoreToQuartile(a.human_score, allScores) === selectedQuartileIndex);
    }

    return list;
  }, [data, severityFilter, selectedQuartileIndex, allScores]);

  const selectedAnswer = useMemo(
    () => displayed.find((a) => String(a.id) === String(selectedStudentId)) ?? displayed[0] ?? null,
    [displayed, selectedStudentId],
  );

  /**
   * Dwell-time tracker — fires answer_view_end when the selected answer changes
   * or the component unmounts.
   *
   * Placed after selectedAnswer useMemo so the closure captures the correct value.
   * Uses navigator.sendBeacon() in the cleanup function to guarantee delivery
   * even if the tab is being closed or the component is unmounting during
   * navigation. This is the correct replacement for the unreliable beforeunload
   * pattern (browsers throttle/cancel fetch() during unload, but sendBeacon()
   * is queued by the browser and delivered asynchronously even after the page closes).
   *
   * Only active in study mode (studyCondition provided).
   */
  useEffect(() => {
    if (!studyCondition || !selectedAnswer) return;

    // Capture the answer and start time that were active when this effect ran.
    // These are closed over by the cleanup function below.
    const answerId = selectedAnswer.id;
    const answerForEnd = selectedAnswer;
    const startTime = answerViewStartRef.current ?? Date.now();
    // Benchmark tagging — closed over at effect-run time (correct answer is in scope).
    // undefined for non-seeded answers; injected only for the 8 strategic trap cases.
    const benchmarkCase = getBenchmarkCase(selectedAnswer.id);
    // FNV-1a hash of student answer text — FERPA compliance, never raw text in logs.
    const answerHash = fnv1a(selectedAnswer.student_answer);

    return () => {
      const dwellTime = Date.now() - startTime;
      // React 18 Strict Mode intentionally unmounts + remounts every component on
      // initial render in development. The resulting cleanup fires with dwellTime ≈ 0–5 ms,
      // which would log a spurious answer_view_end with near-zero dwell time.
      // Filtering below 50 ms silences Strict Mode blips while preserving real navigation
      // (real minimum dwell is constrained by browser repaint + click latency ≥ 100 ms).
      if (dwellTime < 50) return;
      const endPayload: AnswerDwellPayload = {
        student_answer_id: answerId,
        concept_id: conceptId,
        severity: answerForEnd.severity,
        chain_pct: answerForEnd.chain_pct,
        solo_level: answerForEnd.solo,
        bloom_level: answerForEnd.bloom,
        dwell_time_ms: dwellTime,
        capture_method: getBeaconCaptureMethod(),
        trace_panel_open: tracePanelOpen,
        kg_panel_open: kgPanelOpen,
        benchmark_case: benchmarkCase,
        answer_content_hash: answerHash,
      };
      logBeacon(studyCondition, dataset, 'answer_view_end', endPayload as unknown as Record<string, unknown>);
    };
  // Re-run when the selected answer changes (captures dwell on each individual answer).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAnswer?.id, studyCondition]);

  const handleSelectStudent = (answer: ConceptStudentAnswer) => {
    const id = answer.id;
    latestSelectedIdRef.current = id;

    // ── Study-mode: log answer_view_start ──────────────────────────────────────
    if (studyCondition) {
      answerViewStartRef.current = Date.now();
      const startPayload: AnswerDwellPayload = {
        student_answer_id: id,
        concept_id: conceptId,
        severity: answer.severity,
        chain_pct: answer.chain_pct,
        solo_level: answer.solo,
        bloom_level: answer.bloom,
        dwell_time_ms: null,
        // 'start' sentinel — explicit discriminator for post-study event joins.
        // Joining on student_answer_id+session_id is unambiguous via event_type, but
        // 'start' makes SQL/pandas queries self-describing without relying on null semantics.
        capture_method: 'start',
        trace_panel_open: tracePanelOpen,
        kg_panel_open: kgPanelOpen,
        // Benchmark seeding — undefined for non-strategic answers; injected invisibly
        // when the educator naturally navigates to one of the 8 trap cases via the heatmap.
        // Raw answer text is NEVER logged — only the FNV-1a hash (FERPA compliance).
        //
        // Condition A filter: fluent_hallucination and partial_credit_needle traps are
        // only detectable via the VerifierReasoningPanel (Condition B only). Injecting
        // those labels for Condition A views would contaminate the dwell_by_benchmark
        // analysis with structurally-undetectable cases. Score-visible traps
        // (unorthodox_genius, lexical_bluffer) are retained for both conditions.
        benchmark_case: (() => {
          const bc = getBenchmarkCase(answer.id);
          if (!bc) return undefined;
          if (studyCondition === 'A' &&
              (bc === 'fluent_hallucination' || bc === 'partial_credit_needle')) {
            return undefined;
          }
          return bc;
        })(),
        answer_content_hash: fnv1a(answer.student_answer),
      };
      logEvent(studyCondition, dataset, 'answer_view_start', startPayload as unknown as Record<string, unknown>);
    }
    // ─────────────────────────────────────────────────────────────────────────

    // Immediately register selection — detail pane updates at once.
    // Setting empty concepts + loading=true tells the KG panel to dim nodes + show spinner.
    selectStudent(id, []);
    setStudentOverlayLoading(true);

    // Async XAI fetch — resolves KG overlay colours ~200–500 ms later.
    fetch(`${apiBase}/api/visualization/datasets/${dataset}/sample/${id}`)
      .then((r) => (r.ok ? (r.json() as Promise<SampleXAIData>) : Promise.reject()))
      .then((d) => {
        // Guard: ignore result if user has already clicked a different student
        if (latestSelectedIdRef.current === id) {
          selectStudent(id, d.matched_concepts); // also clears studentOverlayLoading via context
        } else {
          setStudentOverlayLoading(false);
        }
      })
      .catch(() => {
        if (latestSelectedIdRef.current === id) {
          setStudentOverlayError(true); // SET_ERROR also clears loading via reducer
        }
      });
  };

  const severityOptions = [
    { value: 'all', label: 'All' },
    { value: 'critical', label: 'Critical' },
    { value: 'moderate', label: 'Moderate' },
    { value: 'minor', label: 'Minor' },
    { value: 'matched', label: 'Covered' },
  ];

  return (
    <Box sx={{ border: '1px solid #e5e7eb', borderRadius: 2, bgcolor: 'background.paper', boxShadow: 2, overflow: 'hidden' }}>
      {/* Header */}
      <Box display="flex" alignItems="center" justifyContent="space-between" px={2} py={1.5} sx={{ borderBottom: '1px solid #f3f4f6' }}>
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            {data ? data.concept_name : conceptId.replace(/_/g, ' ')}
          </Typography>
          {data?.concept_description && (
            <Typography variant="caption" color="text.secondary">{data.concept_description}</Typography>
          )}
        </Box>
        <Box display="flex" gap={1} alignItems="center">
          {onShowKG && (
            <Tooltip title="View KG subgraph for this concept">
              <IconButton size="small" onClick={onShowKG} sx={{ fontSize: 12, color: 'primary.main' }}>
                KG
              </IconButton>
            </Tooltip>
          )}
          <IconButton size="small" onClick={onClose}><CloseIcon fontSize="small" /></IconButton>
        </Box>
      </Box>

      {/* Stats + severity filter */}
      {data && (
        <Box display="flex" alignItems="center" gap={2} px={2} py={1} sx={{ borderBottom: '1px solid #f3f4f6', flexWrap: 'wrap' }}>
          <Chip label={`${data.matched_count} covered`} size="small" sx={{ bgcolor: '#dcfce7', color: '#16a34a', fontWeight: 700 }} />
          <Chip label={`${data.missed_count} missed`} size="small" sx={{ bgcolor: '#fee2e2', color: '#dc2626', fontWeight: 700 }} />
          {selectedQuartileIndex !== null && (
            <Chip label={`Radar Q${selectedQuartileIndex + 1} filter active`} size="small" color="primary" variant="outlined" />
          )}
          <Box display="flex" alignItems="center" gap={0.5} ml="auto">
            <FilterListIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
            <ToggleButtonGroup
              value={severityFilter}
              exclusive
              onChange={(_e, v) => { if (v) setSeverityFilter(v); }}
              size="small"
              sx={{ '& .MuiToggleButton-root': { py: 0.25, px: 1, fontSize: 10 } }}
            >
              {severityOptions.map((o) => (
                <ToggleButton key={o.value} value={o.value}>{o.label}</ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
        </Box>
      )}

      {/* Loading / error */}
      {loading && <Box display="flex" justifyContent="center" py={4}><CircularProgress size={28} /></Box>}
      {error && <Alert severity="error" sx={{ m: 2 }}>Could not load answers: {error}</Alert>}

      {/* Master-Detail body */}
      {!loading && !error && (
        <Box display="flex" sx={{ height: 420 }}>
          {/* LEFT — student list */}
          <Box sx={{ width: 280, flexShrink: 0, borderRight: '1px solid #f3f4f6', overflowY: 'auto' }}>
            {displayed.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
                No students match the current filter.
              </Typography>
            ) : (
              displayed.map((answer) => (
                <StudentListItem
                  key={answer.id}
                  answer={answer}
                  isSelected={String(answer.id) === String(selectedStudentId) || (selectedStudentId === null && answer === displayed[0])}
                  isConditionA={studyCondition === 'A'}
                  onClick={() => handleSelectStudent(answer)}
                />
              ))
            )}
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', p: 1, textAlign: 'center' }}>
              {displayed.length} students
            </Typography>
          </Box>

          {/* RIGHT — detail pane */}
          <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
            {selectedAnswer ? (
              <StudentDetailPane answer={selectedAnswer} isConditionA={studyCondition === 'A'} />
            ) : (
              <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                <Typography variant="body2" color="text.secondary">Select a student from the list</Typography>
              </Box>
            )}
          </Box>
        </Box>
      )}
    </Box>
  );
};
