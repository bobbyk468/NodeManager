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
  | 'chart_click'
  | 'trace_interact'
  | 'rubric_edit'
  | 'answer_view_start'
  | 'answer_view_end'
  | 'kg_node_drag'
  | 'xai_pill_hover';

export interface RubricEditPayload {
  edit_type: 'add' | 'remove' | 'increase_weight' | 'decrease_weight';
  concept_id: string;
  concept_label: string;
  // Whether any CONTRADICTS interaction occurred within each time window before this edit.
  // Primary window is 30 s; 15 s and 60 s reported for sensitivity analysis.
  within_15s: boolean;
  within_30s: boolean;
  within_60s: boolean;
  // ms since the most recent CONTRADICTS interaction (null = no prior interaction this session).
  time_since_last_contradicts_ms: number | null;
  // All CONTRADICTS node IDs in the 60-second rolling window at the moment of edit.
  source_contradicts_nodes_60s: string[];
  // Exact ID match: edited concept_id ∈ session_contradicts_nodes.
  concept_in_contradicts_exact: boolean;
  // Semantic match via Levenshtein ratio ≥ 0.80 or domain alias dictionary.
  concept_in_contradicts_semantic: boolean;
  semantic_match_score: number | null;
  semantic_match_node: string | null;
  // Full set of CONTRADICTS node IDs accumulated this session.
  session_contradicts_nodes: string[];
  // Unix ms when the RubricEditorPanel first rendered.
  panel_mount_timestamp_ms: number;
  // True if the panel was opened before the educator clicked any trace step.
  panel_focus_before_trace: boolean;
  interaction_source: 'click_to_add' | 'manual';
  // Number of structural leaps in the most recently viewed LRM trace.
  trace_gap_count: number;
  // Fraction of trace steps with ≥1 kg_node ∈ [0, 1].
  grounding_density: number;
  // Total concepts visible in the RubricEditorPanel at edit time.
  rubric_size: number;
}

export interface AnswerDwellPayload {
  student_answer_id: string | number;
  concept_id: string;
  severity: string;
  chain_pct: string;
  solo_level: string;
  bloom_level: string;
  // Populated only in answer_view_end; null in answer_view_start.
  dwell_time_ms: number | null;
  /**
   * 'beacon_sent'    — navigator.sendBeacon() queued to backend (reliable delivery).
   * 'beacon_ls_only' — localStorage-only fallback; at-risk if the tab closes before export.
   * 'cleanup'        — React useEffect cleanup during normal navigation.
   * 'start'          — view_start event; end capture method not yet determined.
   */
  capture_method: 'start' | 'beacon_sent' | 'beacon_ls_only' | 'cleanup' | null;
  trace_panel_open: boolean;
  kg_panel_open: boolean;
  benchmark_case?: 'fluent_hallucination' | 'unorthodox_genius' | 'lexical_bluffer' | 'partial_credit_needle';
  /**
   * FNV-1a hash of the student answer text.
   * Raw answer text is never included in event logs — only this deterministic hash.
   */
  answer_content_hash?: string;
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

/**
 * Callback invoked when BOTH localStorage and the backend POST fail for the same event.
 * Set by InstructorDashboard to show a fatal error overlay that blocks session continuation.
 */
let onDualWriteFailure: (() => void) | null = null;
export function setDualWriteFailureHandler(handler: () => void): void {
  onDualWriteFailure = handler;
}

/** Returns true if the write succeeded (any path), false if localStorage failed. */
function safeLocalStorageAppend(event: StudyEvent): boolean {
  try {
    const existing: StudyEvent[] = JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]');
    existing.push(event);
    localStorage.setItem(LOG_KEY, JSON.stringify(existing));
    return true;
  } catch (e) {
    if (e instanceof DOMException) {
      if (e.name === 'QuotaExceededError') {
        try {
          const existing: StudyEvent[] = JSON.parse(localStorage.getItem(LOG_KEY) ?? '[]');
          const trimmed = existing.slice(Math.floor(existing.length * 0.2));
          trimmed.push(event);
          localStorage.setItem(LOG_KEY, JSON.stringify(trimmed));
          if (import.meta.env.DEV) {
            console.warn('[StudyLog] localStorage quota hit — trimmed oldest 20% of events');
          }
          return true;
        } catch {
          return false;
        }
      }
      // SecurityError (strict private browsing quota=0) or other DOMException
      return false;
    } else if (e instanceof SyntaxError) {
      localStorage.removeItem(LOG_KEY);
      try {
        localStorage.setItem(LOG_KEY, JSON.stringify([event]));
        return true;
      } catch {
        return false;
      }
    }
    return false;
  }
}

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

  const localOk = safeLocalStorageAppend(event);

  if (studyApiBase) {
    fetch(`${studyApiBase}/api/study/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    }).catch(() => {
      if (!localOk && onDualWriteFailure) onDualWriteFailure();
    });
  } else if (!localOk && onDualWriteFailure) {
    onDualWriteFailure();
  }

  if (import.meta.env.DEV) {
    console.log('[StudyLog]', event);
  }
}

/**
 * logBeacon — fire-and-forget event delivery via navigator.sendBeacon().
 *
 * Use this inside React useEffect cleanup functions where the component is
 * unmounting. sendBeacon() queues the POST asynchronously and guarantees
 * delivery even when the page is being unloaded — unlike fetch(), which
 * browsers cancel during unload. Falls back to localStorage-only when
 * studyApiBase is not configured.
 *
 * Call getBeaconCaptureMethod() before constructing the payload to embed the
 * correct capture_method discriminator in the event.
 */
export function getBeaconCaptureMethod(): 'beacon_sent' | 'beacon_ls_only' {
  return studyApiBase ? 'beacon_sent' : 'beacon_ls_only';
}

export function logBeacon<T extends Record<string, unknown>>(
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

  safeLocalStorageAppend(event);

  if (studyApiBase) {
    const blob = new Blob([JSON.stringify(event)], { type: 'application/json' });
    navigator.sendBeacon(`${studyApiBase}/api/study/log`, blob);
  }

  if (import.meta.env.DEV) {
    console.log('[StudyBeacon]', event);
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
