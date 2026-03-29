import { test, expect } from '@playwright/test'

test.describe('Suite 3 — Frontend Routing', () => {
  test('3.1 home page — title, links to editor / student / validation', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/node grade/i)
    await expect(page.locator('a[href*="/ws/editor"]')).toBeVisible()
    await expect(page.locator('a[href*="/ws/student"]')).toBeVisible()
    await expect(page.locator('a[href*="/validation"]')).toBeVisible()
  })

  test('3.2 editor route loads without error', async ({ page }) => {
    await page.goto('/ws/editor/local/1/1')
    await expect(page.locator('body')).not.toContainText('Something went wrong')
    // canvas or app bar should be visible
    await expect(page.locator('#root')).not.toBeEmpty()
  })

  test('3.3 student route loads without error', async ({ page }) => {
    await page.goto('/ws/student/local/1/1')
    await expect(page.locator('body')).not.toContainText('Something went wrong')
    await expect(page.locator('#root')).not.toBeEmpty()
  })

  test('3.4 validation dashboard route renders heading', async ({ page }) => {
    await page.goto('/validation')
    await expect(page.locator('h5, h4, h3').filter({ hasText: /NodeGrade.*Validation/i })).toBeVisible({ timeout: 10_000 })
  })
})
