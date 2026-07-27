import { expect, test } from '@playwright/test'

test.describe('Suite 10 — Instructor Dashboard', () => {
  test('10.1 loads dashboard header and metrics', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.getByText('ConceptGrade — Instructor Analytics Dashboard')).toBeVisible({
      timeout: 20_000,
    })
    await expect(page.getByText('Total Answers')).toBeVisible()
    await expect(page.getByText('C5 MAE')).toBeVisible()
    await expect(page.getByText('No Matched Concepts')).toBeVisible()
  })

  test('10.2 condition A hides analytics grid but keeps metric cards', async ({ page }) => {
    await page.goto('/dashboard?condition=A')
    await expect(page.getByText('Study Task')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText('Total Answers')).toBeVisible()
    await expect(page.getByText("Bloom's Taxonomy Distribution")).toHaveCount(0)
    await expect(page.getByText('Per-Sample Score Table')).toHaveCount(0)
  })

  test('10.3 condition B shows analytics sections and table', async ({ page }) => {
    await page.goto('/dashboard?condition=B')
    await expect(page.getByText('Study Task')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByText("Bloom's Taxonomy Distribution")).toBeVisible()
    await expect(page.getByText('Per-Sample Score Table')).toBeVisible()
  })

  test('10.4 row expansion opens score provenance panel', async ({ page }) => {
    await page.goto('/dashboard?condition=B')
    await expect(page.getByText('Per-Sample Score Table')).toBeVisible({ timeout: 20_000 })
    const firstDataRow = page.locator('tbody tr').first()
    await firstDataRow.click()
    await expect(page.getByText('Score Provenance — Sample #')).toBeVisible()
  })
})
