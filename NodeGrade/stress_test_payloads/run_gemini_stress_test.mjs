/**
 * Gemini-Generated Stress Test — 18 Scenarios
 * Runs all scenarios against the live ConceptGrade backend
 * and validates results against Gemini-defined expected ranges.
 */
import { createRequire } from 'module'
import { readFileSync, writeFileSync } from 'fs'

const require = createRequire(import.meta.url)
const { io } = require('socket.io-client')

const BACKEND_URL = 'http://localhost:5001'
const GRAPH_PATH = '/ws/student/stack-grade/1'
const PAUSE_MS = 7000
const TIMEOUT_MS = 120000

const scenarios = JSON.parse(readFileSync('/tmp/all_scenarios.json', 'utf8'))

function grade(answer) {
  return new Promise((resolve) => {
    const socket = io(BACKEND_URL, { transports: ['websocket'] })
    const outputs = {}

    const timer = setTimeout(() => {
      socket.disconnect()
      resolve(null)
    }, TIMEOUT_MS)

    socket.on('connect', () => {
      socket.emit('runGraph', { path: GRAPH_PATH, answer })
    })

    socket.on('outputSet', (out) => {
      outputs[out.label || out.uniqueId] = out.value
    })

    socket.on('graphFinished', () => {
      clearTimeout(timer)
      socket.disconnect()
      try {
        const report = JSON.parse(outputs['feedback'] ?? '{}')
        resolve(report)
      } catch {
        resolve(null)
      }
    })

    socket.on('connect_error', (e) => {
      clearTimeout(timer)
      socket.disconnect()
      resolve(null)
    })
  })
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)) }
const icon = (pass) => pass ? '✓' : '✗'

async function run() {
  console.log('╔══════════════════════════════════════════════════════════╗')
  console.log('║  ConceptGrade Gemini Stress Test — 18 Scenarios          ║')
  console.log('╚══════════════════════════════════════════════════════════╝\n')

  const results = []

  for (let i = 0; i < scenarios.length; i++) {
    const s = scenarios[i]
    const words = s.student_answer.split(' ').length
    console.log(`━━━ [${i+1}/18] ${s.scenario_id} | L${s.level} ${s.label} | ${words}w ━━━`)
    console.log(`  Expected: ${s.expected_score_min}–${s.expected_score_max}/5  |  Bloom L${s.expected_bloom_level}`)

    const report = await grade(s.student_answer)

    if (!report || Object.keys(report).length === 0) {
      console.log('  ERROR: no report received (timeout or parse failure)')
      results.push({ ...s, actual_score: null, actual_bloom_level: null, pass: false, error: 'no report' })
      if (i < scenarios.length - 1) await sleep(PAUSE_MS)
      continue
    }

    const rawScore = report.overall_score ?? 0
    const displayScore = parseFloat((rawScore * 5).toFixed(2))
    const bloomLevel = report.blooms?.level ?? null
    const bloomLabel = report.blooms?.label ?? '?'
    const soloLevel = report.solo?.level ?? '?'
    const soloLabel = report.solo?.label ?? '?'
    const numConcepts = report.concept_graph?.concepts?.length ?? '?'
    const miscList = report.misconceptions?.misconceptions ?? []
    const numMisc = miscList.length
    const criticalMisc = miscList.filter(m => m.severity === 'critical').length

    const inRange = displayScore >= s.expected_score_min && displayScore <= s.expected_score_max
    const bloomMatch = bloomLevel === s.expected_bloom_level
    const pass = inRange && bloomMatch

    console.log(`  Score:    ${displayScore}/5  [${s.expected_score_min}–${s.expected_score_max}]  ${icon(inRange)}`)
    console.log(`  Bloom's:  L${bloomLevel} ${bloomLabel}  (expected L${s.expected_bloom_level})  ${icon(bloomMatch)}`)
    console.log(`  SOLO:     L${soloLevel} ${soloLabel}  |  Concepts: ${numConcepts}  |  Misc: ${numMisc} (${criticalMisc} crit)`)
    if (report.score_rationale) console.log(`  Rationale: ${report.score_rationale.substring(0, 140)}`)
    if (report.blooms?.reasoning) console.log(`  CoT: ${report.blooms.reasoning.substring(0, 130)}`)
    console.log(`  → ${pass ? 'PASS' : 'FAIL'}`)

    results.push({
      scenario_id: s.scenario_id,
      level: s.level,
      label: s.label,
      description: s.description,
      expected_score_min: s.expected_score_min,
      expected_score_max: s.expected_score_max,
      expected_bloom_level: s.expected_bloom_level,
      expected_misconceptions: s.expected_misconceptions,
      actual_score: displayScore,
      actual_bloom_level: bloomLevel,
      actual_bloom_label: bloomLabel,
      actual_solo_level: soloLevel,
      actual_solo_label: soloLabel,
      num_concepts: numConcepts,
      num_misconceptions: numMisc,
      critical_misconceptions: criticalMisc,
      score_in_range: inRange,
      bloom_match: bloomMatch,
      pass,
      rationale: report.score_rationale || '',
      cot_blooms: report.blooms?.reasoning || '',
    })

    if (i < scenarios.length - 1) {
      process.stdout.write(`  [Pausing ${PAUSE_MS/1000}s...]\n`)
      await sleep(PAUSE_MS)
    }
  }

  // Summary
  console.log('\n╔═══════════════════════════════════════════════════════════════════════════════════════════╗')
  console.log('║  FINAL SUMMARY                                                                            ║')
  console.log('╚═══════════════════════════════════════════════════════════════════════════════════════════╝')
  console.log('Scenario                  Lvl  Expected      Got      Bloom Exp→Got   Score   Bloom   Overall')
  console.log('─'.repeat(95))

  let passed = 0
  for (const r of results) {
    if (r.pass) passed++
    const scoreStr = r.actual_score !== null ? `${r.actual_score}/5` : 'ERR'
    const rangeStr = `${r.expected_score_min}-${r.expected_score_max}`
    const bloomStr = `L${r.expected_bloom_level}→L${r.actual_bloom_level ?? '?'}`
    const scoreIcon = r.score_in_range ? '✓' : '✗'
    const bloomIcon = r.bloom_match ? '✓' : '✗'
    const passStr = r.pass ? '✓ PASS' : '✗ FAIL'
    console.log(
      `${r.scenario_id.padEnd(26)}L${r.level}   ${rangeStr.padEnd(13)}${scoreStr.padEnd(9)}${bloomStr.padEnd(15)}${scoreIcon}       ${bloomIcon}       ${passStr}`
    )
  }

  const pct = ((passed / results.length) * 100).toFixed(0)
  console.log('─'.repeat(95))
  console.log(`\nResult: ${passed}/${results.length} PASSED (${pct}%)`)

  // Score vs expected breakdown by level
  console.log('\nScore deviation by Bloom level:')
  for (let l = 1; l <= 6; l++) {
    const lr = results.filter(r => r.level === l && r.actual_score !== null)
    if (lr.length === 0) continue
    const avgScore = (lr.reduce((a, r) => a + r.actual_score, 0) / lr.length).toFixed(2)
    const midpoint = ((lr[0].expected_score_min + lr[0].expected_score_max) / 2).toFixed(2)
    const allPass = lr.every(r => r.pass) ? '✓' : '✗'
    console.log(`  L${l} (${lr[0].label}): avg=${avgScore}/5  mid=${midpoint}/5  ${allPass}`)
  }

  writeFileSync('/tmp/stress_results.json', JSON.stringify(results, null, 2))
  console.log('\nFull results saved to /tmp/stress_results.json')
  process.exit(0)
}

run().catch(e => { console.error('Fatal:', e); process.exit(1) })
