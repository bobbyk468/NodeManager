/**
 * DashboardContext — shared selection state enabling bidirectional brushing.
 *
 * Any component can read or write:
 *   selectedConcept / selectedSeverity  — from heatmap cell click
 *   selectedStudentId                   — from answer panel row click
 *   selectedStudentMatchedConcepts      — concept IDs the selected student covered
 *   selectedQuartileIndex               — 0-3 from radar quartile click (Q1–Q4)
 *
 * Bidirectional links implemented:
 *   Heatmap cell click  → StudentAnswerPanel (already done via props)
 *   Radar quartile click → StudentAnswerPanel score-range filter
 *   StudentAnswerPanel row click → KG subgraph node coloring
 *
 * State machine implemented as useReducer so that cross-selection clearing rules
 * (e.g. switching concepts must clear the student selection) are centralised and testable.
 */

import React, { createContext, useContext, useReducer } from 'react';

export interface ContradictsEntry {
  nodeId:       string;
  timestamp_ms: number;
}

// Entries older than this are pruned when a new one arrives.
// Inner 15 s and 30 s windows are computed at read time in RubricEditorPanel.
const ROLLING_WINDOW_MS = 60_000;

interface DashboardSelectionState {
  selectedConcept: string | null;
  selectedSeverity: string | null;
  selectedStudentId: string | number | null;
  selectedStudentMatchedConcepts: string[];
  studentOverlayLoading: boolean;
  studentOverlayError: boolean;
  // Radar → answer panel filter
  selectedQuartileIndex: number | null;
  // Rolling 60-second window of CONTRADICTS interactions; pruned on every write.
  recentContradicts: ContradictsEntry[];
  // Gap count from the most recently rendered LRM trace; logged on each rubric edit.
  lastTraceGapCount: number;
  // Fraction of trace steps with ≥1 kg_node ∈ [0, 1]; logged on each rubric edit.
  lastGroundingDensity: number;
  // True while a VerifierReasoningPanel trace is expanded.
  traceOpen: boolean;
}

type DashboardAction =
  | { type: 'SELECT_CONCEPT'; concept: string | null; severity: string | null }
  | { type: 'SELECT_STUDENT'; id: string | number | null; matchedConcepts: string[] }
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_ERROR'; error: boolean }
  | { type: 'SELECT_QUARTILE'; index: number | null }
  | { type: 'PUSH_CONTRADICTS'; nodeId: string }
  | { type: 'SET_TRACE_GAP_COUNT'; count: number }
  | { type: 'SET_GROUNDING_DENSITY'; density: number }
  | { type: 'SET_TRACE_OPEN'; open: boolean }
  | { type: 'CLEAR_ALL' };

const INITIAL_STATE: DashboardSelectionState = {
  selectedConcept: null,
  selectedSeverity: null,
  selectedStudentId: null,
  selectedStudentMatchedConcepts: [],
  studentOverlayLoading: false,
  studentOverlayError: false,
  selectedQuartileIndex: null,
  recentContradicts: [],
  lastTraceGapCount: 0,
  lastGroundingDensity: 0,
  traceOpen: false,
};

function dashboardReducer(
  state: DashboardSelectionState,
  action: DashboardAction,
): DashboardSelectionState {
  switch (action.type) {
    case 'SELECT_CONCEPT':
      return {
        ...state,
        selectedConcept: action.concept,
        selectedSeverity: action.severity,
        selectedStudentId: null,
        selectedStudentMatchedConcepts: [],
        studentOverlayLoading: false,
        studentOverlayError: false,
      };
    case 'SELECT_STUDENT':
      return {
        ...state,
        selectedStudentId: action.id,
        selectedStudentMatchedConcepts: action.matchedConcepts,
        studentOverlayLoading: false,
        studentOverlayError: false,
      };
    case 'SET_LOADING':
      return { ...state, studentOverlayLoading: action.loading, studentOverlayError: false };
    case 'SET_ERROR':
      return { ...state, studentOverlayError: action.error, studentOverlayLoading: false };
    case 'SELECT_QUARTILE':
      return {
        ...state,
        selectedQuartileIndex: action.index,
        selectedStudentId: null,
        selectedStudentMatchedConcepts: [],
        studentOverlayLoading: false,
        studentOverlayError: false,
      };
    case 'PUSH_CONTRADICTS': {
      const now = Date.now();
      const pruned = state.recentContradicts.filter(
        e => now - e.timestamp_ms < ROLLING_WINDOW_MS,
      );
      return {
        ...state,
        recentContradicts: [...pruned, { nodeId: action.nodeId, timestamp_ms: now }],
      };
    }
    case 'SET_TRACE_GAP_COUNT':
      return { ...state, lastTraceGapCount: action.count };
    case 'SET_GROUNDING_DENSITY':
      return { ...state, lastGroundingDensity: action.density };
    case 'SET_TRACE_OPEN':
      return { ...state, traceOpen: action.open };
    case 'CLEAR_ALL':
      return INITIAL_STATE;
    default:
      return state;
  }
}

interface DashboardSelectionActions {
  selectConcept: (concept: string | null, severity?: string | null) => void;
  selectStudent: (id: string | number | null, matchedConcepts?: string[]) => void;
  setStudentOverlayLoading: (loading: boolean) => void;
  setStudentOverlayError: (error: boolean) => void;
  selectQuartile: (quartileIndex: number | null) => void;
  pushContradicts: (nodeId: string) => void;
  setTraceGapCount: (count: number) => void;
  setGroundingDensity: (density: number) => void;
  setTraceOpen: (open: boolean) => void;
  clearAll: () => void;
}

type DashboardContextValue = DashboardSelectionState & DashboardSelectionActions;

const DashboardContext = createContext<DashboardContextValue>({
  ...INITIAL_STATE,
  selectConcept: () => {},
  selectStudent: () => {},
  setStudentOverlayLoading: () => {},
  setStudentOverlayError: () => {},
  selectQuartile: () => {},
  pushContradicts: () => {},
  setTraceGapCount: () => {},
  setGroundingDensity: () => {},
  setTraceOpen: () => {},
  clearAll: () => {},
});

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(dashboardReducer, INITIAL_STATE);

  const selectConcept = (concept: string | null, severity: string | null = null) =>
    dispatch({ type: 'SELECT_CONCEPT', concept, severity });

  const selectStudent = (id: string | number | null, matchedConcepts: string[] = []) =>
    dispatch({ type: 'SELECT_STUDENT', id, matchedConcepts });

  const setStudentOverlayLoading = (loading: boolean) =>
    dispatch({ type: 'SET_LOADING', loading });

  const setStudentOverlayError = (error: boolean) =>
    dispatch({ type: 'SET_ERROR', error });

  const selectQuartile = (index: number | null) =>
    dispatch({ type: 'SELECT_QUARTILE', index });

  const pushContradicts = (nodeId: string) =>
    dispatch({ type: 'PUSH_CONTRADICTS', nodeId });

  const setTraceGapCount = (count: number) =>
    dispatch({ type: 'SET_TRACE_GAP_COUNT', count });

  const setGroundingDensity = (density: number) =>
    dispatch({ type: 'SET_GROUNDING_DENSITY', density });

  const setTraceOpen = (open: boolean) =>
    dispatch({ type: 'SET_TRACE_OPEN', open });

  const clearAll = () => dispatch({ type: 'CLEAR_ALL' });

  return (
    <DashboardContext.Provider
      value={{
        ...state,
        selectConcept,
        selectStudent,
        setStudentOverlayLoading,
        setStudentOverlayError,
        selectQuartile,
        pushContradicts,
        setTraceGapCount,
        setGroundingDensity,
        setTraceOpen,
        clearAll,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  return useContext(DashboardContext);
}
