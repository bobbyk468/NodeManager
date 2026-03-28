/**
 * Real answer test — original answers, no padding.
 * Tests the 4 Bloom's levels with authentic text.
 * Usage: node run_real_test.mjs
 */
import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import path from 'path'

const require = createRequire(import.meta.url)
const { io } = require('socket.io-client')
const __dirname = path.dirname(fileURLToPath(import.meta.url))

const BACKEND_URL = 'http://localhost:5001'
const GRAPH_PATH = '/ws/student/stack-grade/1'

const TEST_CASES = [
  {
    level: 'L1_Recall',
    expected: '~1.5/5',
    answer: `A stack is a basic data structure in computer science. It uses the LIFO rule, which stands for last in, first out. The two main things you can do with it are push to add an item, and pop to take an item off.`
  },
  {
    level: 'L2_Understand',
    expected: '~2.5/5',
    answer: `A stack is a linear abstract data type based on the LIFO (Last-In-First-Out) principle. This means the newest element added is the first one removed. The core operations are push, which inserts an element at the top, and pop, which removes the top element. Another operation is peek, which lets you look at the top item without removing it. You can implement a stack using either an array or a linked list. Arrays are easier but have a fixed size, while linked lists can grow but use more memory for pointers. Stacks are used for undo buttons in software and browser history.`
  },
  {
    level: 'L4_Analyze',
    expected: '~3.8/5',
    answer: `A Stack operates on a strictly Last-In, First-Out (LIFO) ordering principle. This sequential restriction ensures that operations only ever occur at a single designated end, called the "top".

Structurally, stacks are implemented via dynamic arrays or singly linked lists, each presenting distinct trade-offs. The array implementation yields excellent spatial locality, resulting in highly efficient CPU cache utilization. However, it requires amortized O(1) time for the push operation because the underlying contiguous memory must occasionally be doubled and copied when capacity is reached. Conversely, the linked list implementation provides strictly O(1) time for all operations, as no resizing is required. The trade-off is poor cache performance due to memory fragmentation and the spatial overhead of storing node pointers.

Because of its LIFO nature, stacks are deeply embedded in computational architecture. They manage subroutine execution via the function call stack, where activation records are pushed upon invocation and popped upon return, natively enabling recursion. They are also the fundamental structure behind Depth-First Search (DFS) algorithms, backtracking logic, and syntax parsing like the shunting-yard algorithm.`
  },
  {
    level: 'L6_Create',
    expected: '5.0/5',
    answer: `While standard array and linked-list implementations of stacks are sufficient for single-threaded environments, their reliance on a unified 'top' pointer creates severe contention in highly concurrent systems. To resolve this, I propose a novel architecture: the "Segmented Epoch Stack".

Instead of a single atomic head pointer which suffers from CAS (Compare-And-Swap) failure loops under high thread contention, the Segmented Epoch Stack divides the LIFO structure into thread-local sub-stacks (epochs). When a thread executes a push, it writes strictly to its local epoch buffer in strictly O(1) time without acquiring a global lock. A background synchronization thread utilizes a read-copy-update (RCU) mechanism to flush these local buffers into the global immutable linked-list stack during low-contention micro-intervals.

For the pop operation, if a thread's local buffer is empty, it uses hazard pointers to safely pop from the global stack without ABA vulnerabilities. By sacrificing strict global chronological ordering for thread-local chronological ordering, this architecture bypasses the fundamental hardware limits of cache-line invalidation on the top pointer, making it uniquely suited for extreme-throughput event-processing systems.`
  }
]

async function runCase(tc) {
  return new Promise((resolve) => {
    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)
    console.log(`▶ ${tc.level} (${tc.answer.split(' ').length} words) — Expected: ${tc.expected}`)
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`)

    const socket = io(BACKEND_URL, { transports: ['websocket'] })
    const results = {}
    const start = Date.now()

    const timeout = setTimeout(() => {
      socket.disconnect()
      resolve({ ...tc, score: 'TIMEOUT', elapsed: '120s' })
    }, 120_000)

    socket.on('connect', () => {
      socket.emit('runGraph', { path: GRAPH_PATH, answer: tc.answer })
    })

    socket.on('outputSet', (out) => {
      results[out.label || out.uniqueId] = out.value
    })

    socket.on('graphFinished', () => {
      clearTimeout(timeout)
      const elapsed = ((Date.now() - start) / 1000).toFixed(1)
      const raw = parseFloat(results['overall score'] ?? results['4'] ?? '0')
      const score = isNaN(raw) ? '?' : (raw <= 1 ? raw * 5 : raw).toFixed(2)

      let bloomsLabel='?', soloLabel='?', concepts='?', rationale='', reasoning='', misconceptions=[]
      try {
        const r = JSON.parse(results['feedback'] ?? '{}')
        bloomsLabel = r.blooms?.label ?? '?'
        soloLabel = r.solo?.label ?? '?'
        concepts = r.concept_graph?.concepts?.length ?? '?'
        rationale = r.score_rationale ?? ''
        reasoning = r.blooms?.reasoning ?? ''
        misconceptions = r.misconceptions?.misconceptions ?? []
      } catch {}

      console.log(`  Score:        ${score} / 5  (expected ${tc.expected})`)
      console.log(`  Bloom's:      ${bloomsLabel}`)
      console.log(`  SOLO:         ${soloLabel}`)
      console.log(`  Concepts:     ${concepts}`)
      if (rationale) console.log(`  Rationale:    ${rationale}`)
      if (reasoning) console.log(`  CoT:          ${reasoning}`)
      if (misconceptions.length > 0) {
        console.log(`  Misconceptions: ${misconceptions.length}`)
        misconceptions.forEach(m => console.log(`    [${m.severity}] ${m.explanation?.substring(0,80)}`))
      }

      socket.disconnect()
      resolve({ ...tc, score, bloomsLabel, soloLabel, concepts, elapsed, rationale })
    })

    socket.on('connect_error', (e) => {
      clearTimeout(timeout)
      socket.disconnect()
      resolve({ ...tc, score: 'CONN_ERR', elapsed: '0s' })
    })
  })
}

async function main() {
  console.log(`\n╔══════════════════════════════════════╗`)
  console.log(`║  ConceptGrade Real-Answer Test       ║`)
  console.log(`║  Upgraded Prompts + Taxonomy         ║`)
  console.log(`╚══════════════════════════════════════╝`)

  const summary = []
  for (const tc of TEST_CASES) {
    const result = await runCase(tc)
    summary.push(result)
    if (tc !== TEST_CASES[TEST_CASES.length - 1]) {
      console.log(`\n  Pausing 8s...`)
      await new Promise(r => setTimeout(r, 8000))
    }
  }

  console.log(`\n╔══════════════════════════════════════╗`)
  console.log(`║           SUMMARY                    ║`)
  console.log(`╚══════════════════════════════════════╝`)
  console.log(`${'Level'.padEnd(16)} ${'Score'.padEnd(8)} ${'Expected'.padEnd(10)} ${'Bloom\'s'.padEnd(12)} ${'SOLO'.padEnd(22)} ${'Concepts'.padEnd(10)} Time`)
  console.log('─'.repeat(95))
  for (const r of summary) {
    const ok = r.score !== 'TIMEOUT' && r.score !== 'CONN_ERR' ? '✓' : '✗'
    console.log(`${ok} ${r.level.padEnd(15)} ${String(r.score).padEnd(8)} ${r.expected.padEnd(10)} ${String(r.bloomsLabel).padEnd(12)} ${String(r.soloLabel).padEnd(22)} ${String(r.concepts).padEnd(10)} ${r.elapsed}s`)
  }
  console.log()
}

main().catch(console.error)
