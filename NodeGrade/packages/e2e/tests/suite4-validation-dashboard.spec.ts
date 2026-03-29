import { test, expect } from '@playwright/test'

test.describe('Suite 4 — Validation Dashboard Behaviour', () => {
  test('4.1 auto-runs on load — spinner then results appear', async ({ page }) => {
    await page.goto('/validation')
    // Spinner or "Running checks…" should appear immediately
    const spinner = page.getByText('Running checks…')
    // Wait for it to disappear (checks complete)
    await expect(spinner).not.toBeVisible({ timeout: 20_000 })
    // At least one table row should now be visible
    await expect(page.locator('tbody tr').first()).toBeVisible()
  })

  test('4.2 summary chip shows passed / skipped / failed counts', async ({ page }) => {
    await page.goto('/validation')
    await expect(page.getByText('Running checks…')).not.toBeVisible({ timeout: 20_000 })
    const chip = page.locator('.MuiChip-filled')
    await expect(chip).toContainText(/passed/)
    await expect(chip).toContainText(/skipped|failed/)
  })

  test('4.3 no FAIL rows after successful run', async ({ page }) => {
    await page.goto('/validation')
    await expect(page.getByText('Running checks…')).not.toBeVisible({ timeout: 20_000 })
    // Wait for rows to be rendered
    await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 })
    // All FAIL chips should be absent
    const failChips = page.locator('.MuiChip-colorError').filter({ hasText: 'FAIL' })
    await expect(failChips).toHaveCount(0)
    // At least 19 rows total
    const count = await page.locator('tbody tr').count()
    expect(count).toBeGreaterThanOrEqual(19)
  })

  test('4.4 refresh button re-runs checks and updates timestamp', async ({ page }) => {
    await page.goto('/validation')
    await expect(page.getByText('Running checks…')).not.toBeVisible({ timeout: 20_000 })
    const ts1 = await page.locator('text=/Checks evaluated at:/').textContent()
    await page.waitForTimeout(1500)
    await page.locator('[aria-label="Re-run all checks"]').click()
    await expect(page.getByText('Running checks…')).not.toBeVisible({ timeout: 20_000 })
    const ts2 = await page.locator('text=/Checks evaluated at:/').textContent()
    expect(ts2).not.toBe(ts1)
  })

  test('4.5 report timestamps shown for jest / vitest / integration sections', async ({ page }) => {
    await page.goto('/validation')
    await expect(page.getByText('Running checks…')).not.toBeVisible({ timeout: 20_000 })
    await expect(page.locator('text=/report generated:/').first()).toBeVisible()
    const timestamps = await page.locator('text=/report generated:/').all()
    expect(timestamps.length).toBeGreaterThanOrEqual(3)
  })
})
