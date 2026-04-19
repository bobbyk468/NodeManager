import { Injectable } from '@nestjs/common';
import { appendFile, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import * as path from 'path';

// Mirror DATA_DIR convention from visualization.service — four levels up from compiled output.
const LOGS_DIR = path.resolve(__dirname, '../../../../concept-aware/data/study_logs');

@Injectable()
export class StudyService {
  /**
   * Append a single study event to a per-session JSONL file.
   * Each line is a valid JSON object; the file can be read back with
   * `[JSON.parse(line) for line in file.read_text().splitlines()]`.
   *
   * The session-scoped filename prevents concurrent writes from interleaving
   * across participants: each participant writes to their own file.
   */
  async appendEvent(event: unknown): Promise<{ ok: boolean; error?: string }> {
    if (!existsSync(LOGS_DIR)) {
      await mkdir(LOGS_DIR, { recursive: true });
    }

    const sessionId =
      typeof event === 'object' && event !== null && 'session_id' in event
        ? String((event as Record<string, unknown>).session_id)
        : 'unknown';

    // Sanitise: keep only alphanumeric, hyphens, and underscores.
    const safeName = sessionId.replace(/[^a-zA-Z0-9-_]/g, '_');
    const logPath = path.join(LOGS_DIR, `${safeName}.jsonl`);

    try {
      await appendFile(logPath, JSON.stringify(event) + '\n', 'utf8');
      return { ok: true };
    } catch (e) {
      const err = e as NodeJS.ErrnoException;
      const msg = `[StudyService] Failed to append event: ${err.code} — ${err.message}`;
      console.error(msg);
      // Return ok:false instead of throwing — disk errors must never surface as 5xx
      // to study participants, whose localStorage copy remains the fallback.
      return { ok: false, error: msg };
    }
  }
}
