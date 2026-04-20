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
import { fnv1a } from '../../utils/hash';
import { AnswerDwellPayload, getBeaconCaptureMethod, logBeacon, logEvent } from '../../utils/studyLogger';

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

      {/* Scores */}
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

      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
        Question
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontStyle: 'italic', fontSize: 11 }}>
        {answer.question}
      </Typography>

      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
        Student answer
      </Typography>
      <Box sx={{ p: 1.5, bgcolor: isConditionA ? '#f8fafc' : `${color}0d`, borderRadius: 1, border: `1px solid ${isConditionA ? '#e2e8f0' : `${color}33`}`, mb: 1.5 }}>
        <Typography variant="body2" sx={{ lineHeight: 1.6, fontStyle: 'italic' }}>
          "{answer.student_answer}"
        </Typography>
      </Box>

      {/* KG metadata */}
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
  const latestSelectedIdRef = useRef<string | number | null>(null);
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

  useEffect(() => {
    if (!studyCondition || !selectedAnswer) return;

    const answerId = selectedAnswer.id;
    const answerForEnd = selectedAnswer;
    const startTime = answerViewStartRef.current ?? Date.now();
    const benchmarkCase = getBenchmarkCase(selectedAnswer.id);
    const answerHash = fnv1a(selectedAnswer.student_answer);

    return () => {
      const dwellTime = Date.now() - startTime;
      // React 18 Strict Mode fires cleanup immediately on mount (~0–5 ms).
      // 50 ms threshold silences those blips; real navigation is always ≥ 100 ms.
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

    if (studyCondition) {
      answerViewStartRef.current = Date.now();
      // Condition A: suppress trace-only trap types (fluent_hallucination, partial_credit_needle)
      // since those are only visible via VerifierReasoningPanel, which Condition A lacks.
      const bc = getBenchmarkCase(answer.id);
      const benchmarkCase = bc && studyCondition === 'A' &&
        (bc === 'fluent_hallucination' || bc === 'partial_credit_needle')
        ? undefined
        : bc;
      const startPayload: AnswerDwellPayload = {
        student_answer_id: id,
        concept_id: conceptId,
        severity: answer.severity,
        chain_pct: answer.chain_pct,
        solo_level: answer.solo,
        bloom_level: answer.bloom,
        dwell_time_ms: null,
        capture_method: 'start',
        trace_panel_open: tracePanelOpen,
        kg_panel_open: kgPanelOpen,
        benchmark_case: benchmarkCase,
        answer_content_hash: fnv1a(answer.student_answer),
      };
      logEvent(studyCondition, dataset, 'answer_view_start', startPayload as unknown as Record<string, unknown>);
    }

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
