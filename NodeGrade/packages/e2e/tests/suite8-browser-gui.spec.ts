import { test, expect } from '@playwright/test'

// All tests run inside a real Chromium browser context
test.describe('Suite 8 — Browser / GUI Checks', () => {
  test.beforeEach(async ({ page }) => {
    // Load the app so window APIs are available
    await page.goto('/validation')
    await expect(page.getByText('Running checks…')).not.toBeVisible({ timeout: 20_000 })
  })

  test('8.1 localStorage read/write (dark mode persistence)', async ({ page }) => {
    const result = await page.evaluate(() => {
      localStorage.setItem('ng-gui-test', '1')
      const val = localStorage.getItem('ng-gui-test')
      localStorage.removeItem('ng-gui-test')
      return val
    })
    expect(result).toBe('1')
    // Confirm cleanup
    const afterCleanup = await page.evaluate(() => localStorage.getItem('ng-gui-test'))
    expect(afterCleanup).toBeNull()
  })

  test('8.2 matchMedia API — returns boolean matches field', async ({ page }) => {
    const matches = await page.evaluate(() => {
      const mq = window.matchMedia('(prefers-color-scheme: dark)')
      return typeof mq.matches
    })
    expect(matches).toBe('boolean')
  })

  test('8.3 History API available (SPA routing)', async ({ page }) => {
    const available = await page.evaluate(() => typeof window.history?.pushState === 'function')
    expect(available).toBe(true)
  })

  test('8.4 document.title contains "Node Grade"', async ({ page }) => {
    const title = await page.title()
    expect(title.toLowerCase()).toMatch(/node.?grade/i)
  })

  test('8.5 WebSocket handshake to backend succeeds within 3s', async ({ page }) => {
    const connected = await page.evaluate(() =>
      new Promise<boolean>((resolve) => {
        const ws = new WebSocket('ws://localhost:5001/socket.io/?EIO=4&transport=websocket')
        const timer = setTimeout(() => { ws.close(); resolve(false) }, 3000)
        ws.onopen = () => { clearTimeout(timer); ws.close(); resolve(true) }
        ws.onerror = () => { clearTimeout(timer); resolve(false) }
      })
    )
    expect(connected).toBe(true)
  })
})
