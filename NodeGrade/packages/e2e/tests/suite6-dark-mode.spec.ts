import { test, expect } from '@playwright/test'

test.describe('Suite 6 — Dark Mode', () => {
  test('6.1 dark mode toggle button is present in editor toolbar', async ({ page }) => {
    await page.goto('/ws/editor/local/1/1')
    // Wait for the app bar to mount
    await expect(page.locator('[aria-label="toggle color mode"]')).toBeVisible({ timeout: 10_000 })
  })

  test('6.2 dark mode persists across reload via localStorage', async ({ page }) => {
    await page.goto('/ws/editor/local/1/1')
    await expect(page.locator('[aria-label="toggle color mode"]')).toBeVisible({ timeout: 10_000 })

    // Read current mode from localStorage
    const before = await page.evaluate(() => localStorage.getItem('ng-color-mode'))

    // Toggle the mode
    await page.locator('[aria-label="toggle color mode"]').click()
    const after = await page.evaluate(() => localStorage.getItem('ng-color-mode'))
    expect(after).not.toBe(before)

    // Reload and confirm mode was restored
    await page.reload()
    await expect(page.locator('[aria-label="toggle color mode"]')).toBeVisible({ timeout: 10_000 })
    const reloaded = await page.evaluate(() => localStorage.getItem('ng-color-mode'))
    expect(reloaded).toBe(after)
  })
})
