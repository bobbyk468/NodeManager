export type StudyCondition = 'A' | 'B';

/**
 * Optional backend API base URL for server-side log durability.
 * Call setStudyApiBase(apiBase) once on study mount (e.g. in InstructorDashboard useEffect).
 * When set, every event is also POSTed to POST /api/study/log as a backup in case
 * the participant closes the browser tab before exporting the localStorage log.
 */
let studyApiBase: string | null = null;
export function setStudyApiBase(apiBase: string): void {
  studyApiBase = apiBase.replace(/\/$/, '');
}

export type StudyEventType =
  | 'page_view'
  | 'tab_change'
  | 'task_start'
  | 'task_submit'
  | 'chart_hover'
  | 'trace_interact'   // educator clicks a CONTRADICTS/SUPPORTS/UNCERTAIN step in trace panel
  | 'rubric_edit';     // educator flags a rubric concept for add / remove / reweight

/**
 * Payload schema for rubric_edit events.
 * Captured atomically at edit time for causal proximity analysis.
 *
 * Multi-window design (pre-registered, no researcher DoF):
 *   within_15s / within_30s / within_60s — report all three; primary is 30 s.
 *   source_contradicts_nodes_60s         — any-event model (not just the last event).
 *
 * Semantic alignment uses fuzzy matching (conceptAliases.ts) to handle lexical
 * variation (e.g. "learning rate" vs "step_size").
 */
export interface RubricEditPayload {
  edit_type: 'add' | 'remove' | 'increase_weight' | 'decrease_weight';
  concept_id: string;
  concept_label: string;
  // ── Multi-window causal attribution ──────────────────────────────────────────
  // Whether any CONTRADICTS interaction occurred within each pre-registered window.
  within_15s: boolean;
  within_30s: boolean;
  within_60s: boolean;
  // ms since the most recent CONTRADICTS interaction (null = no prior interaction ever).
  time_since_last_contradicts_ms: number | null;
  // All CONTRADICTS node IDs in the 60-second rolling window at the moment of edit.
  // Implements the "any-event" attribution model.
  source_contradicts_nodes_60s: string[];
  // ── Concept alignment ────────────────────────────────────────────────────────
  // Exact ID match: edited concept_id ∈ session_contradicts_nodes.
  concept_in_contradicts_exact: boolean;
  // Semantic match: edited concept fuzzy-matches a session CONTRADICTS node
  // via Levenshtein ratio ≥ 0.80 or domain alias dictionary.
  concept_in_contradicts_semantic: boolean;
  semantic_match_score: number | null;   // 0–1 similarity score of the best match
  semantic_match_node: string | null;    // CONTRADICTS nodeId that matched
  // Full set of CONTRADICTS node IDs accumulated this session.
  session_contradicts_nodes: string[];
  // ── Panel timing ────────────────────────────────────────────────────────────
  // Unix ms when the RubricEditorPanel first rendered (panel_mount_timestamp = first view).
  panel_mount_timestamp_ms: number;
  // True if the panel was shown BEFORE the educator had interacted with any trace.
  // Distinguishes "rubric-first" from "trace-first" reasoning strategies.
  panel_focus_before_trace: boolean;
  // ── Interaction source ───────────────────────────────────────────────────────
  // 'click_to_add'  = educator clicked a CONTRADICTS chip directly (zero lexical ambiguity).
  // 'manual'        = educator clicked an edit button on the rubric concept list.
  interaction_source: 'click_to_add' | 'manual';
  // ── Topological gap & grounding density (moderators) ────────────────────────
  // Number of structural leaps in the most recently viewed LRM trace.
  // Moderator variable for H1: do gappier traces elicit higher causal attribution?
  trace_gap_count: number;
  // Grounding Density of the most recently viewed LRM trace ∈ [0, 1].
  // Fraction of steps with ≥1 kg_node. Used in Stability Analysis (Section 5a)
  // to compare Gemini Flash vs. DeepSeek-R1 and as a secondary H1 moderator.
  grounding_density: number;
}

export interface StudyEvent {
  session_id: string;
  condition: StudyCondition;
  dataset: string;
  event_type: StudyEventType;
  timestamp_ms: number;
  elapsed_ms: number;
  payload: Record<string, unknown>;
}

const SESSION_START = Date.now();
const SESSION_ID = typeof crypto !== 'undefined' && crypto.randomUUID
  ? crypto.randomUUID()
  : `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
const LOG_KEY = 'ng-study-log';

export function logEvent<T extends Record<string, unknown>>(
  condition: string,
  dataset: string,
  event_type: StudyEventType,
  payload: T = {} as T,
): void {
  const event: StudyEvent = {
    session_id: SESSION_ID,
    condition: condition as StudyCondition,
    dataset,
    event_type,
    timestamp_ms: Date.now(),
    elapsed_ms: Date.now() - SESSION_START,
    payload,
  };

  try {
    const existing: StudyEvent[] = JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]');
    existing.push(event);
    localStorage.setItem(LOG_KEY, JSON.stringify(existing));
  } catch {
    // localStorage unavailable — silently skip
  }

  // Fire-and-forget to backend for IRB-grade durability.
  // localStorage alone is insufficient: a tab crash or accidental close loses all data.
  if (studyApiBase) {
    fetch(`${studyApiBase}/api/study/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    }).catch(() => {
      // Backend unreachable — localStorage remains the fallback, no user-visible error.
    });
  }

  if (import.meta.env.DEV) {
    console.log('[StudyLog]', event);
  }
}

export function exportStudyLog(): string {
  try {
    return localStorage.getItem(LOG_KEY) ?? '[]';
  } catch {
    return '[]';
  }
}

export function clearStudyLog(): void {
  try {
    localStorage.removeItem(LOG_KEY);
  } catch {
    // silently skip
  }
}

export { SESSION_ID };
