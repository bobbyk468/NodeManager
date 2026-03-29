import { test, expect } from '@playwright/test'

const API = 'http://localhost:5001'

test.describe('Suite 1 — Backend API Health', () => {
  test('1.1 health endpoint returns ok + db up', async ({ request }) => {
    const res = await request.get(`${API}/health`)
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(body.status).toBe('ok')
    expect(body.components?.database?.status).toBe('up')
  })

  test('1.2 graphs endpoint returns non-empty array', async ({ request }) => {
    const res = await request.get(`${API}/graphs`)
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(Array.isArray(body)).toBe(true)
    expect(body.length).toBeGreaterThan(0)
  })

  test('1.3 unknown route returns 404', async ({ request }) => {
    const res = await request.get(`${API}/nonexistent-route`)
    expect(res.status()).toBe(404)
  })
})
