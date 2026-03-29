import { test, expect } from '@playwright/test'

const API = 'http://localhost:5001'

test.describe('Suite 7 — WeightedScore Integration', () => {
  test('7.1 integration report: weightedScore value = 82.5, expected = 82.5', async ({ request }) => {
    const res = await request.get(`${API}/reports/integration-results.json`)
    expect(res.status()).toBe(200)
    const body = await res.json()
    const ws = body.tests?.weightedScore
    expect(ws?.value).toBeCloseTo(82.5, 2)
    expect(ws?.expected).toBe(82.5)
    // Confirm arithmetic: score_1=80, score_2=0.85 (→85), weights=0.5/0.5 → 82.5
    expect(Math.abs(ws.value - 82.5)).toBeLessThanOrEqual(0.01)
  })
})
