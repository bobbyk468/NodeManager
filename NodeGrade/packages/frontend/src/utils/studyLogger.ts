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
  | 'chart_hover'   // mouse enters a chart container
  | 'chart_click'   // deliberate click inside a chart (quartile select, row expand, etc.)
  | 'trace_interact'     // educator clicks a CONTRADICTS/SUPPORTS/UNCERTAIN step in trace panel
  | 'rubric_edit'        // educator flags a rubric concept for add / remove / reweight
  | 'answer_view_start'  // educator selects a student answer (drill-down begins)
  | 'answer_view_end'    // educator navigates away from answer (dwell window closes)
  | 'kg_node_drag'       // educator drags a KG node to rearrange the subgraph layout
  | 'xai_pill_hover';    // educator hovers a matched/missing concept pill in XAI provenance panel

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
  // ── Rubric population ───────────────────────────────────────────────────────
  // Total concepts visible in the RubricEditorPanel at edit time.
  // Needed by analyze_study_logs.py for the hypergeometric null model (H2):
  // true rubric size N, not just the count of edited concepts.
  rubric_size: number;
}

/**
 * Payload for answer_view_start / answer_view_end events.
 *
 * Design notes (per pre-registered analysis plan):
 *   - student_answer_id is the opaque ID from ConceptStudentAnswer; analysts join
 *     this with trm_metrics_cache.json to get leap_count / grounding_density.
 *   - chain_pct, solo_level, bloom_level are KG-coverage proxies available at click
 *     time without a round-trip, enabling fast dwell-time analysis without re-fetching.
 *   - dwell_time_ms is null in answer_view_start; populated in answer_view_end.
 *     Computed as cleanup time − mount time inside useEffect; delivered via
 *     navigator.sendBeacon() to survive tab unloads (fixes the beforeunload problem).
 *   - capture_method distinguishes normal navigation ('cleanup') from page unload
 *     ('beacon') so analysts can flag incomplete sessions.
 */
export interface AnswerDwellPayload {
  student_answer_id: string | number;
  concept_id: string;
  severity: string;
  // KG-coverage proxy metrics (from ConceptStudentAnswer — no extra fetch required)
  chain_pct: string;
  solo_level: string;
  bloom_level: string;
  // Populated only in answer_view_end; null in answer_view_start
  dwell_time_ms: number | null;
  // How the end event was captured
  /**
   * 'beacon_sent'    — navigator.sendBeacon() was queued to the backend (reliable delivery).
   * 'beacon_ls_only' — no backend configured; localStorage-only fallback (at-risk on tab close).
   * 'cleanup'        — React useEffect cleanup fired during normal navigation (fetch-based).
   * null             — view_start event; end capture method not yet determined.
   *
   * Post-study auditing: sessions with only 'beacon_ls_only' end events should be flagged
   * for data completeness review — they may be missing if the participant closed the tab
   * before localStorage could be exported.
   */
  capture_method: 'start' | 'beacon_sent' | 'beacon_ls_only' | 'cleanup' | null;
  // Interaction context at the moment of selection
  trace_panel_open: boolean;
  kg_panel_open: boolean;
  /**
   * Injected when the viewed answer matches one of the strategic benchmark seeds
   * (see benchmarkSeeds.ts). Undefined for non-seeded answers.
   * Used post-study to measure whether Condition B outperforms A on each trap type.
   */
  benchmark_case?: 'fluent_hallucination' | 'unorthodox_genius' | 'lexical_bluffer' | 'partial_credit_needle';
  /**
   * FNV-1a hash of the student answer text (32-bit, hex string).
   * FERPA compliance: raw answer text is never included in event logs — only this
   * deterministic hash. Allows analysts to verify the same answer was shown
   * consistently across participants without exposing student PII.
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
 * This prevents a participant from completing a session whose data cannot be recorded,
 * satisfying the IRB requirement that all consent-to-record sessions produce usable data.
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
          return false; // Still full after trim
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

  // Fire-and-forget to backend for IRB-grade durability.
  // If localStorage also failed, trigger the dual-write failure handler so the
  // study facilitator is alerted before the participant's session data is lost.
  if (studyApiBase) {
    fetch(`${studyApiBase}/api/study/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    }).catch(() => {
      // Backend unreachable AND localStorage failed → both channels down → fatal.
      if (!localOk && onDualWriteFailure) onDualWriteFailure();
    });
  } else if (!localOk && onDualWriteFailure) {
    // No backend configured AND localStorage failed → same fatal condition.
    onDualWriteFailure();
  }

  if (import.meta.env.DEV) {
    console.log('[StudyLog]', event);
  }
}

/**
 * logBeacon — fire-and-forget event delivery via navigator.sendBeacon().
 *
 * Use this ONLY inside React useEffect cleanup functions or visibilitychange
 * handlers where the component is unmounting and a normal fetch() would be
 * cancelled by the browser before it completes.
 *
 * sendBeacon() queues the POST asynchronously and guarantees delivery even
 * when the page is being unloaded, making it the correct choice for
 * answer_view_end events captured during React cleanup.
 *
 * Falls back to localStorage-only if studyApiBase is not set (local dev without backend).
 *
 * Call `getBeaconCaptureMethod()` BEFORE constructing the payload to embed the correct
 * `capture_method` value — distinguishes 'beacon_sent' (backend queued) from
 * 'beacon_ls_only' (localStorage-only fallback, at-risk on tab close).
 */

/**
 * Returns the capture_method value that logBeacon will use for this session.
 * Call at payload-construction time so the discriminator is embedded in the event.
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

  // Persist to localStorage as fallback (best-effort; discriminated error handling)
  safeLocalStorageAppend(event);

  // Reliable delivery during unmount via Beacon API
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
