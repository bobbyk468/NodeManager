/**
 * Stress test: injects 50k-word answers directly via socket.io
 * Usage: node run_stress_test.mjs <level>
 *   level: L1 | L2 | L4 | L6 (default: all, sequential)
 *
 * Prerequisites: npm install socket.io-client (run once in this dir)
 */
import { readFileSync } from 'fs'
import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import path from 'path'

const require = createRequire(import.meta.url)
const { io } = require('socket.io-client')

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const BACKEND_URL = 'http://localhost:5001'
// Graph path for the Stack question
const GRAPH_PATH = '/ws/student/stack-grade/1'

const LEVELS = ['L1_Recall', 'L2_Understand', 'L4_Analyze', 'L6_Create']
const EXPECTED = { L1_Recall: '~1.5', L2_Understand: '~2.5', L4_Analyze: '~3.8', L6_Create: '5.0' }

const targetLevel = process.argv[2]
const levelsToTest = targetLevel
  ? LEVELS.filter(l => l.startsWith(targetLevel))
  : LEVELS

async function runLevel(level) {
  const filePath = path.join(__dirname, `${level}_50k_words.txt`)
  const answer = readFileSync(filePath, 'utf-8')
  const wordCount = answer.split(/\s+/).length

  return new Promise((resolve, reject) => {
    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)
    console.log(`▶ Testing ${level} (${wordCount.toLocaleString()} words)`)
    console.log(`  Expected score: ${EXPECTED[level]}/5`)
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)

    const socket = io(BACKEND_URL, { transports: ['websocket'] })
    const results = {}
    const startTime = Date.now()
    let timeout

    socket.on('connect', () => {
      console.log(`  Connected. Submitting answer to ${GRAPH_PATH}...`)
      timeout = setTimeout(() => {
        console.error(`  ⏰ TIMEOUT after 3 minutes`)
        socket.disconnect()
        resolve({ level, score: 'TIMEOUT', elapsed: '180s', results })
      }, 180_000)
      socket.emit('runGraph', { path: GRAPH_PATH, answer })
    })

    socket.on('outputSet', (output) => {
      console.log(`  [outputSet] uniqueId=${output.uniqueId} label=${output.label} type=${output.type} value=${String(output.value).substring(0, 60)}`)
      results[output.label || output.uniqueId] = output.value
    })

    socket.on('graphFinished', () => {
      clearTimeout(timeout)
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)
      const score = results['overall score'] ?? results['-1'] ?? '?'
      const depth = results['depth category'] ?? results['-2'] ?? '?'

      // Parse feedback for Bloom's/SOLO
      let bloomsLabel = '?', soloLabel = '?', numConcepts = '?', rationale = ''
      try {
        const report = JSON.parse(results['feedback'] ?? results['-3'] ?? '{}')
        bloomsLabel = report.blooms?.label ?? '?'
        soloLabel = report.solo?.label ?? '?'
        numConcepts = report.concept_graph?.concepts?.length ?? '?'
        rationale = report.score_rationale ?? ''
      } catch { /* skip */ }

      const displayScore = parseFloat(score) <= 1 ? (parseFloat(score) * 5).toFixed(2) : score

      console.log(`\n  ✅ RESULT (${elapsed}s):`)
      console.log(`     Score:      ${displayScore} / 5  (expected ${EXPECTED[level]})`)
      console.log(`     Depth:      ${depth}`)
      console.log(`     Bloom's:    ${bloomsLabel}`)
      console.log(`     SOLO:       ${soloLabel}`)
      console.log(`     Concepts:   ${numConcepts}`)
      if (rationale) console.log(`     Rationale:  ${rationale}`)

      socket.disconnect()
      resolve({ level, score: displayScore, depth, bloomsLabel, soloLabel, numConcepts, elapsed, rationale })
    })

    socket.on('nodeErrorOccured', (err) => {
      console.error(`  ❌ Node error: ${err.error}`)
    })

    socket.on('connect_error', (err) => {
      clearTimeout(timeout)
      console.error(`  ❌ Connection failed: ${err.message}`)
      socket.disconnect()
      reject(err)
    })
  })
}

async function main() {
  console.log(`\n╔══════════════════════════════════════╗`)
  console.log(`║  ConceptGrade 50k-Word Stress Test   ║`)
  console.log(`╚══════════════════════════════════════╝`)
  console.log(`  Levels to test: ${levelsToTest.join(', ')}`)

  const summary = []
  for (const level of levelsToTest) {
    try {
      const result = await runLevel(level)
      summary.push(result)
      // Brief pause between runs
      if (levelsToTest.indexOf(level) < levelsToTest.length - 1) {
        console.log(`\n  Pausing 5s before next level...`)
        await new Promise(r => setTimeout(r, 5000))
      }
    } catch (err) {
      console.error(`  Failed: ${err.message}`)
    }
  }

  console.log(`\n╔══════════════════════════════════════╗`)
  console.log(`║           SUMMARY TABLE              ║`)
  console.log(`╚══════════════════════════════════════╝`)
  console.log(`${'Level'.padEnd(16)} ${'Score'.padEnd(8)} ${'Expected'.padEnd(10)} ${'Bloom\'s'.padEnd(12)} ${'SOLO'.padEnd(20)} Time`)
  console.log('─'.repeat(80))
  for (const r of summary) {
    const pass = r.score !== 'TIMEOUT' ? '✓' : '✗'
    console.log(`${pass} ${r.level.padEnd(15)} ${String(r.score).padEnd(8)} ${EXPECTED[r.level].padEnd(10)} ${String(r.bloomsLabel).padEnd(12)} ${String(r.soloLabel).padEnd(20)} ${r.elapsed}s`)
  }
  console.log()
}

main().catch(console.error)
