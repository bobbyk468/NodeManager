import { Body, Controller, Get, Post } from '@nestjs/common';
import { StudyService } from './study.service';

@Controller('api/study')
export class StudyController {
  constructor(private readonly studyService: StudyService) {}

  /**
   * GET /api/study/health
   * Lightweight liveness probe for the study facilitator. Returns 200 { status: 'ok' }
   * when the backend is reachable and the study log directory is writable.
   * Intentionally does not check Prisma — the visualization module never uses it.
   */
  @Get('health')
  studyHealth(): { status: string; timestamp: string } {
    return { status: 'ok', timestamp: new Date().toISOString() };
  }

  /**
   * POST /api/study/log
   * Receives a single study event JSON object and appends it to the
   * participant's per-session JSONL file on disk.
   *
   * Returns 200 with { ok: boolean, error?: string }. Returns ok:false (not 5xx)
   * on disk write failures so the participant session is never interrupted.
   * Callers use fire-and-forget .catch() — the response body is for IRB audit only.
   */
  @Post('log')
  async logEvent(@Body() event: unknown): Promise<{ ok: boolean; error?: string }> {
    return this.studyService.appendEvent(event);
  }
}
