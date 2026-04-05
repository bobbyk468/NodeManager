import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import RefreshIcon from '@mui/icons-material/Refresh'
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography
} from '@mui/material'
import { useCallback, useEffect, useState } from 'react'

import { getConfig } from '@/utils/config'

type CheckStatus = 'pass' | 'fail' | 'skip' | 'pending'

interface CheckResult {
  label: string
  status: CheckStatus
  detail?: string
}

interface Section {
  title: string
  checks: CheckResult[]
  reportTimestamp?: string
  stale?: boolean
}

const STALE_THRESHOLD_MS = 2 * 60 * 60 * 1000 // 2 hours

// Use the backend API to proxy report files so the path is not hardcoded to
// one machine. Falls back to the Vite @fs dev endpoint when API is unavailable.
function reportUrl(filename: string, api: string): string {
  return `${api}/reports/${filename}`
}

async function safeFetch(url: string): Promise<{ ok: boolean; status: number; body: string; lastModified: string | null }> {
  try {
    const r = await fetch(url, { credentials: 'include' })
    const body = await r.text()
    return { ok: r.ok, status: r.status, body, lastModified: r.headers.get('Last-Modified') }
  } catch (e: unknown) {
    return { ok: false, status: 0, body: String(e), lastModified: null }
  }
}

function isStale(lastModified: string | null): boolean {
  if (!lastModified) return false
  const age = Date.now() - new Date(lastModified).getTime()
  return age > STALE_THRESHOLD_MS
}

async function runChecks(api: string): Promise<Section[]> {
  // ── 1. Backend Jest ──────────────────────────────────────────────────────
  const jestRes = await safeFetch(reportUrl('jest-results.json', api))
  const jestChecks: CheckResult[] = []
  let jestTimestamp: string | undefined
  if (!jestRes.ok) {
    jestChecks.push({
      label: 'jest-results.json readable',
      status: 'fail',
      detail: `HTTP ${jestRes.status} — run: yarn workspace backend test:report`
    })
  } else {
    const j = JSON.parse(jestRes.body)
    jestTimestamp = j.testResults?.[0]?.endTime
      ? new Date(j.testResults[0].endTime).toLocaleString()
      : undefined
    jestChecks.push({
      label: 'No failed test suites',
      status: j.numFailedTestSuites === 0 ? 'pass' : 'fail',
      detail: `numFailedTestSuites=${j.numFailedTestSuites}`
    })
    jestChecks.push({
      label: `numPassedTests = ${j.numPassedTests} (≥ 40)`,
      status: j.numPassedTests >= 40 ? 'pass' : 'fail',
      detail: `numPassedTests=${j.numPassedTests}`
    })
    jestChecks.push({
      label: 'success === true',
      status: j.success ? 'pass' : 'fail',
      detail: `success=${j.success}`
    })
  }

  // ── 2. Frontend Vitest ───────────────────────────────────────────────────
  const vitestRes = await safeFetch(reportUrl('vitest-results.json', api))
  const vitestChecks: CheckResult[] = []
  let vitestTimestamp: string | undefined
  if (!vitestRes.ok) {
    vitestChecks.push({
      label: 'vitest-results.json readable',
      status: 'fail',
      detail: `HTTP ${vitestRes.status} — run: yarn workspace @haski/ta-frontend test`
    })
  } else {
    const v = JSON.parse(vitestRes.body)
    const suites: Array<{ status: string; endTime?: number; assertionResults: Array<{ status: string }> }> =
      v.testResults ?? []
    const allPassed = suites.length > 0 && suites.every((s) => s.status === 'passed')
    const passedAssertions = suites.reduce(
      (sum, s) => sum + s.assertionResults.filter((a) => a.status === 'passed').length,
      0
    )
    const lastEnd = suites.reduce((max, s) => Math.max(max, s.endTime ?? 0), 0)
    vitestTimestamp = lastEnd ? new Date(lastEnd).toLocaleString() : undefined
    vitestChecks.push({
      label: 'Test suites present',
      status: suites.length > 0 ? 'pass' : 'fail',
      detail: `${suites.length} suite(s)`
    })
    vitestChecks.push({
      label: 'All suites passed',
      status: allPassed ? 'pass' : 'fail',
      detail: suites.map((s) => s.status).join(', ')
    })
    vitestChecks.push({
      label: `Node-registration assertions passed (≥ 6, got ${passedAssertions})`,
      status: passedAssertions >= 6 ? 'pass' : 'fail',
      detail: `${passedAssertions} passed`
    })
  }

  // ── 3. Integration ───────────────────────────────────────────────────────
  const intRes = await safeFetch(reportUrl('integration-results.json', api))
  const intChecks: CheckResult[] = []
  let intTimestamp: string | undefined
  if (!intRes.ok) {
    intChecks.push({
      label: 'integration-results.json readable',
      status: 'fail',
      detail: `HTTP ${intRes.status} — run: yarn workspace backend test:integration`
    })
  } else {
    const i = JSON.parse(intRes.body)
    intTimestamp = i.timestamp ? new Date(i.timestamp).toLocaleString() : undefined
    const ws = i.tests?.weightedScore
    const llm = i.tests?.llmJson
    intChecks.push({
      label: 'WeightedScore passed',
      status: ws?.status === 'passed' ? 'pass' : 'fail',
      detail: `status=${ws?.status}, value=${ws?.value}`
    })
    intChecks.push({
      label: `WeightedScore value ≈ ${ws?.expected ?? 82.5} (got ${ws?.value})`,
      status: typeof ws?.value === 'number' && Math.abs(ws.value - (ws?.expected ?? 82.5)) <= 0.01
        ? 'pass'
        : 'fail',
      detail: `value=${ws?.value}, expected=${ws?.expected ?? 82.5}`
    })
    intChecks.push({
      label: 'LLM test not failed',
      status: llm?.status === 'failed' ? 'fail' : llm?.status === 'skipped' ? 'skip' : 'pass',
      detail: llm?.status === 'skipped' ? `skipped — ${llm?.reason}` : `status=${llm?.status}`
    })
    intChecks.push({
      label: 'Overall success',
      status: i.success ? 'pass' : 'fail',
      detail: `success=${i.success}`
    })
  }

  // ── 4. Live smoke tests ──────────────────────────────────────────────────
  const [healthRes, graphsRes, homeRes, editorRes, studentRes] = await Promise.all([
    safeFetch(`${api}/health`),
    safeFetch(`${api}/graphs`),
    safeFetch(window.location.origin + '/'),
    safeFetch(window.location.origin + '/ws/editor/local/1/1'),
    safeFetch(window.location.origin + '/ws/student/local/1/1')
  ])

  let healthOk = false
  let healthDetail = `HTTP ${healthRes.status}`
  if (healthRes.ok) {
    try {
      const hj = JSON.parse(healthRes.body)
      healthOk = hj?.status === 'ok'
      healthDetail = `status=${hj?.status}${hj?.info?.database?.status ? `, db=${hj.info.database.status}` : ''}`
    } catch {
      healthOk = false
    }
  }

  let graphsOk = false
  let graphsDetail = `HTTP ${graphsRes.status}`
  if (graphsRes.ok) {
    try {
      const arr = JSON.parse(graphsRes.body)
      graphsOk = Array.isArray(arr)
      graphsDetail = graphsOk ? `${arr.length} graph(s) in DB` : 'not an array'
    } catch {
      graphsOk = false
    }
  }

  const homeOk = homeRes.ok && homeRes.body.includes('Node Grade')
  const smokeChecks: CheckResult[] = [
    { label: 'Backend health (status: ok)', status: healthOk ? 'pass' : 'fail', detail: healthDetail },
    { label: 'Graphs API returns array', status: graphsOk ? 'pass' : 'fail', detail: graphsDetail },
    { label: 'Frontend home loads (HTTP 200)', status: homeRes.ok ? 'pass' : 'fail', detail: `HTTP ${homeRes.status}` },
    { label: '"Node Grade" in home HTML', status: homeOk ? 'pass' : 'fail', detail: homeOk ? 'found' : 'not found' },
    { label: 'Editor route loads (HTTP 200)', status: editorRes.ok ? 'pass' : 'fail', detail: `HTTP ${editorRes.status}` },
    { label: 'Student route loads (HTTP 200)', status: studentRes.ok ? 'pass' : 'fail', detail: `HTTP ${studentRes.status}` }
  ]

  // ── 5. Browser / GUI checks ──────────────────────────────────────────────
  const guiChecks: CheckResult[] = []

  // 5a. localStorage read/write (dark mode persistence)
  try {
    localStorage.setItem('ng-gui-test', '1')
    const val = localStorage.getItem('ng-gui-test')
    localStorage.removeItem('ng-gui-test')
    guiChecks.push({
      label: 'localStorage read/write (dark mode persistence)',
      status: val === '1' ? 'pass' : 'fail',
      detail: val === '1' ? 'ok' : `got "${val}"`
    })
  } catch (e: unknown) {
    guiChecks.push({ label: 'localStorage read/write (dark mode persistence)', status: 'fail', detail: String(e) })
  }

  // 5b. matchMedia API (system dark mode detection)
  try {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    guiChecks.push({
      label: 'matchMedia API (system dark mode detection)',
      status: typeof mq?.matches === 'boolean' ? 'pass' : 'fail',
      detail: `prefers-dark=${mq.matches}`
    })
  } catch (e: unknown) {
    guiChecks.push({ label: 'matchMedia API (system dark mode detection)', status: 'fail', detail: String(e) })
  }

  // 5c. History API (SPA routing)
  try {
    const ok = typeof window.history?.pushState === 'function'
    guiChecks.push({
      label: 'History API available (SPA routing)',
      status: ok ? 'pass' : 'fail',
      detail: ok ? 'available' : 'not available'
    })
  } catch (e: unknown) {
    guiChecks.push({ label: 'History API available (SPA routing)', status: 'fail', detail: String(e) })
  }

  // 5d. Page title
  const titleOk = document.title.toLowerCase().includes('node grade') || document.title.toLowerCase().includes('nodegrade')
  guiChecks.push({
    label: 'Page <title> contains "Node Grade"',
    status: titleOk ? 'pass' : 'fail',
    detail: `title="${document.title}"`
  })

  // 5e. WebSocket reachable (Socket.IO handshake)
  await new Promise<void>((resolve) => {
    const url = `${api.replace(/^http/, 'ws')}/socket.io/?EIO=4&transport=websocket`
    let done = false
    try {
      const ws = new WebSocket(url)
      const timer = setTimeout(() => {
        if (!done) { done = true; ws.close(); guiChecks.push({ label: 'WebSocket reachable (backend)', status: 'fail', detail: 'timeout after 3 s' }); resolve() }
      }, 3000)
      ws.onopen = () => {
        if (!done) { done = true; clearTimeout(timer); ws.close(); guiChecks.push({ label: 'WebSocket reachable (backend)', status: 'pass', detail: 'connected' }); resolve() }
      }
      ws.onerror = () => {
        if (!done) { done = true; clearTimeout(timer); guiChecks.push({ label: 'WebSocket reachable (backend)', status: 'fail', detail: 'connection error' }); resolve() }
      }
    } catch (e: unknown) {
      if (!done) { done = true; guiChecks.push({ label: 'WebSocket reachable (backend)', status: 'fail', detail: String(e) }); resolve() }
    }
  })

  // ── 7. Templates ─────────────────────────────────────────────────────────
  const [starterRes, conceptRes, llmRes] = await Promise.all([
    safeFetch(window.location.origin + '/templates/starter.json'),
    safeFetch(window.location.origin + '/templates/concept-grade.json'),
    safeFetch(window.location.origin + '/templates/llm-grader.json')
  ])

  function templateCheck(label: string, res: Awaited<ReturnType<typeof safeFetch>>): CheckResult {
    if (!res.ok) return { label, status: 'fail', detail: `HTTP ${res.status}` }
    try {
      const t = JSON.parse(res.body)
      const count = t?.nodes?.length ?? 0
      return { label, status: count > 0 ? 'pass' : 'fail', detail: `${count} node(s)` }
    } catch {
      return { label, status: 'fail', detail: 'invalid JSON' }
    }
  }

  const templateChecks: CheckResult[] = [
    templateCheck('starter.json', starterRes),
    templateCheck('concept-grade.json', conceptRes),
    templateCheck('llm-grader.json', llmRes)
  ]

  return [
    { title: 'Backend Jest', checks: jestChecks, reportTimestamp: jestTimestamp, stale: isStale(jestRes.lastModified) },
    { title: 'Frontend Vitest (node registration)', checks: vitestChecks, reportTimestamp: vitestTimestamp, stale: isStale(vitestRes.lastModified) },
    { title: 'Integration Tests', checks: intChecks, reportTimestamp: intTimestamp, stale: isStale(intRes.lastModified) },
    { title: 'Live Smoke Tests', checks: smokeChecks },
    { title: 'Browser / GUI Checks', checks: guiChecks },
    { title: 'Starter Templates', checks: templateChecks }
  ]
}

function StatusChip({ status }: { status: CheckStatus }) {
  if (status === 'pending') return <CircularProgress size={16} />
  if (status === 'pass')
    return <Chip icon={<CheckCircleIcon />} label="PASS" color="success" size="small" variant="outlined" />
  if (status === 'skip')
    return <Chip icon={<RemoveCircleOutlineIcon />} label="SKIP" color="warning" size="small" variant="outlined" />
  return <Chip icon={<ErrorIcon />} label="FAIL" color="error" size="small" variant="outlined" />
}

export default function ValidationDashboard() {
  const [sections, setSections] = useState<Section[]>([])
  const [running, setRunning] = useState(false)
  const [ranAt, setRanAt] = useState<string | null>(null)
  const [runError, setRunError] = useState<string | null>(null)

  const run = useCallback(async () => {
    setRunning(true)
    setSections([])
    setRunError(null)
    const api = (getConfig().API || 'http://localhost:5001/').replace(/\/$/, '')
    try {
      const result = await runChecks(api)
      setSections(result)
    } catch (e: unknown) {
      setRunError(String(e))
    } finally {
      setRanAt(new Date().toLocaleTimeString())
      setRunning(false)
    }
  }, [])

  useEffect(() => { run() }, [run])

  const allChecks = sections.flatMap((s) => s.checks)
  const total = allChecks.length
  const passed = allChecks.filter((c) => c.status === 'pass').length
  const failed = allChecks.filter((c) => c.status === 'fail').length
  const skipped = allChecks.filter((c) => c.status === 'skip').length

  return (
    <Box sx={{ p: 3, maxWidth: 900, overflowX: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
        <Typography variant="h5">NodeGrade — Validation Dashboard</Typography>
        <Tooltip title="Re-run all checks">
          <span>
            <IconButton onClick={run} disabled={running} size="small">
              <RefreshIcon />
            </IconButton>
          </span>
        </Tooltip>
      </Box>

      {ranAt && !running && (
        <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
          Checks evaluated at: {ranAt}
        </Typography>
      )}

      {running && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, my: 2 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Running checks…</Typography>
        </Box>
      )}

      {runError && (
        <Alert severity="error" sx={{ my: 2 }}>
          Unexpected error during checks: {runError}
        </Alert>
      )}

      {!running && total > 0 && (
        <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap', alignItems: 'center' }}>
          <Chip
            icon={failed === 0 ? <CheckCircleIcon /> : <HelpOutlineIcon />}
            label={`${passed} passed · ${skipped} skipped · ${failed} failed`}
            color={failed === 0 ? 'success' : 'error'}
            variant="filled"
          />
        </Box>
      )}

      {sections.map((section) => (
        <Box key={section.title} sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Typography variant="subtitle1" fontWeight={600}>
              {section.title}
            </Typography>
            {section.reportTimestamp && (
              <Typography variant="caption" color="text.secondary">
                report generated: {section.reportTimestamp}
              </Typography>
            )}
            {section.stale && (
              <Tooltip title="Report file is older than 2 hours — re-run tests to refresh">
                <Chip
                  icon={<WarningAmberIcon />}
                  label="stale"
                  color="warning"
                  size="small"
                  variant="outlined"
                />
              </Tooltip>
            )}
          </Box>
          <Table size="small" sx={{ tableLayout: 'fixed', width: '100%' }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: '50%' }}>Check</TableCell>
                <TableCell sx={{ width: '12%' }}>Status</TableCell>
                <TableCell>Detail</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {section.checks.map((c) => (
                <TableRow key={c.label}>
                  <TableCell sx={{ wordBreak: 'break-word' }}>{c.label}</TableCell>
                  <TableCell>
                    <StatusChip status={c.status} />
                  </TableCell>
                  <TableCell sx={{ wordBreak: 'break-word' }}>
                    <Typography variant="caption" color="text.secondary">
                      {c.detail ?? '—'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Divider sx={{ mt: 2 }} />
        </Box>
      ))}
    </Box>
  )
}
