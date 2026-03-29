import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  globalSetup: './globalSetup',
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [
    ['list'],
    ['json', { outputFile: '../../reports/playwright-results.json' }],
    ['html', { outputFolder: '../../reports/playwright-html', open: 'never' }]
  ],
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    trace: 'on-first-retry'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } }
  ]
})
