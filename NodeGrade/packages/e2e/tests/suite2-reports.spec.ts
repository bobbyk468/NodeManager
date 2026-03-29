import { test, expect } from '@playwright/test'

const API = 'http://localhost:5001'

test.describe('Suite 2 — Report Files Served by Backend', () => {
  test('2.1 jest-results.json — no failures, ≥40 tests, success', async ({ request }) => {
    const res = await request.get(`${API}/reports/jest-results.json`)
    expect(res.status()).toBe(200)
    expect(res.headers()['last-modified']).toBeTruthy()
    const body = await res.json()
    expect(body.numFailedTestSuites).toBe(0)
    expect(body.numPassedTests).toBeGreaterThanOrEqual(40)
    expect(body.success).toBe(true)
  })

  test('2.2 vitest-results.json — suites present, all passed, ≥6 assertions', async ({ request }) => {
    const res = await request.get(`${API}/reports/vitest-results.json`)
    expect(res.status()).toBe(200)
    expect(res.headers()['last-modified']).toBeTruthy()
    const body = await res.json()
    const suites: Array<{ status: string; assertionResults: Array<{ status: string }> }> = body.testResults ?? []
    expect(suites.length).toBeGreaterThan(0)
    expect(suites.every((s) => s.status === 'passed')).toBe(true)
    const passed = suites.reduce((n, s) => n + s.assertionResults.filter((a) => a.status === 'passed').length, 0)
    expect(passed).toBeGreaterThanOrEqual(6)
  })

  test('2.3 integration-results.json — weightedScore passed, value ~82.5, llmJson not failed', async ({ request }) => {
    const res = await request.get(`${API}/reports/integration-results.json`)
    expect(res.status()).toBe(200)
    expect(res.headers()['last-modified']).toBeTruthy()
    const body = await res.json()
    expect(body.tests.weightedScore.status).toBe('passed')
    expect(body.tests.weightedScore.value).toBeCloseTo(82.5, 1)
    expect(body.tests.llmJson.status).not.toBe('failed')
    expect(body.success).toBe(true)
  })

  test('2.4 unknown report returns 404', async ({ request }) => {
    const res = await request.get(`${API}/reports/secrets.json`)
    expect(res.status()).toBe(404)
  })
})
