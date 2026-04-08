export type StudyCondition = 'A' | 'B';

export type StudyEventType =
  | 'page_view'
  | 'tab_change'
  | 'task_start'
  | 'task_submit'
  | 'chart_hover';

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

export function logEvent(
  condition: string,
  dataset: string,
  event_type: StudyEventType,
  payload: Record<string, unknown> = {},
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
