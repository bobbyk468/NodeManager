/**
 * Multi-Domain Stress Test
 * Tests ConceptGradeNode pipeline across Physics, Economics, History, Biology, Math.
 * Calls Gemini directly — no backend needed.
 */
import { readFileSync, writeFileSync } from 'fs'

const GEMINI_KEY = process.env.GEMINI_API_KEY || 'AIzaSyDDYni0ohrWnN_NBfR80CsB8iw-2Mhljrc'
const PAUSE_MS = 5000
const SCENARIOS_FILE = process.argv[2] || '/tmp/new_scenarios.json'

// ─── Gemini helper ─────────────────────────────────────────────────────────
async function callGemini(system, user, maxTokens = 2048, jsonMode = false) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_KEY}`
  const genConfig = { temperature: 0.1, maxOutputTokens: maxTokens, thinkingConfig: { thinkingBudget: 0 } }
  if (jsonMode) genConfig.responseMimeType = 'application/json'
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: system }] },
      contents: [{ parts: [{ text: user }] }],
      generationConfig: genConfig,
    })
  })
  if (!resp.ok) {
    const err = await resp.text()
    throw new Error(`Gemini ${resp.status}: ${err.substring(0, 200)}`)
  }
  const data = await resp.json()
  return data.candidates?.[0]?.content?.parts?.[0]?.text || '{}'
}

// ─── JSON extraction (robust) ────────────────────────────────────────────────
function extractJson(text) {
  let cleaned = text.replace(/```(?:json)?\s*\n?/g, '').replace(/\n?```/g, '').trim()
  const start = cleaned.indexOf('{')
  if (start === -1) return cleaned.trim()
  let depth = 0, inString = false, escape = false
  for (let i = start; i < cleaned.length; i++) {
    const ch = cleaned[i]
    if (escape) { escape = false; continue }
    if (ch === '\\' && inString) { escape = true; continue }
    if (ch === '"') { inString = !inString; continue }
    if (inString) continue
    if (ch === '{') depth++
    else if (ch === '}') { depth--; if (depth === 0) return cleaned.substring(start, i + 1) }
  }
  return cleaned.substring(start)
}

// ─── Domain-agnostic prompts ─────────────────────────────────────────────────
function makeExtractionPrompts(domain, question, answer) {
  const isMath = domain === 'math'
  const system = isMath
    ? `You are an expert Mathematics educator analyzing student answers.
Extract mathematical concepts, methods, and relationships from the student's response.
For math: capture formulas used, proof steps, theorems cited, and whether reasoning is correct.
Keep concept IDs short (snake_case). Limit to at most 12 concepts and 10 relationships.
Relationship types: uses, proves, derives, applies, defines, is_equivalent_to, is_step_of`
    : `You are an expert educator analyzing student answers in ${domain}.
Extract domain concepts and relationships from the student's response.
Keep concept IDs short (snake_case). Limit to at most 12 concepts and 10 relationships.
Relationship types: is_a, has_part, causes, leads_to, uses, contrasts_with, has_property, explains`

  const user = `QUESTION: ${question}

STUDENT ANSWER: ${answer}

Return compact JSON (no whitespace):
{"concepts":[{"id":"name","ok":true}],"relationships":[{"s":"src","t":"tgt","r":"type","ok":true}],"depth":"surface|moderate|deep"}`

  return { system, user }
}

function makeDepthPrompts(domain, question, answer, numConcepts, conceptList, numRels, isolatedCount, isMath) {
  const mathNote = isMath ? `
MATHEMATICS-SPECIFIC RULES:
- L1: States a formula or theorem without explanation (e.g., "A = πr²" with no derivation).
- L2: Explains what a formula means or when to use it.
- L3: Correctly applies a formula or method to solve a specific problem — shows working.
- L4: Derives a result, proves a theorem, or explains WHY a method works from first principles.
- L5: Evaluates which method/approach is better for a given problem type, with explicit justification.
- L6: Proposes a novel proof technique, generalises to a new class of problems, or invents an algorithm.
NOTE: In math, step-by-step calculation applying a known formula = L3 (not L4). Deriving from axioms or proving = L4+.` : ''

  const system = `You are an expert educational assessment researcher. Classify this student response along TWO taxonomies.

⚠ CRITICAL RULE — COGNITIVE LEVEL ≠ CORRECTNESS:
Bloom's level reflects the COGNITIVE OPERATION the student ATTEMPTED, not whether the answer is correct.
DO NOT downgrade Bloom's because of errors. DO NOT upgrade because the answer sounds complex.

1. BLOOM'S REVISED TAXONOMY (1-6):
   1=Remember: Recalls a fact, definition, or formula with no explanation beyond stating it.
   2=Understand: Explains in own words, paraphrases, gives examples. Uses ONE concept to explain ONE phenomenon.
      Example (L2): "Metal feels colder because thermal conductivity transfers heat away from your hand faster."
      Key: even a cause-effect explanation using a single concept stays L2.
   3=Apply: Takes an established principle, law, or framework and uses it to PREDICT or SOLVE a specific new scenario.
      Examples (L3): "Price ceiling below equilibrium → consumers demand more, producers supply less → shortage."
                     "Mutation → better camouflage → higher survival → population proportion shifts over generations."
                     "Applying WWI causes (nationalism, alliances) to predict how a modern conflict could escalate."
      Key: applying a known framework to a scenario = L3, even if the student explains WHY within that framework.
   4=Analyze: Deconstructs a COMPLEX system into MULTIPLE interacting components, OR compares MULTIPLE alternatives with mechanistic evidence of WHY they differ.
      True L4 examples: Explaining a refrigerator cycle (compressor→condenser→expansion valve→evaporator — all components, all interactions). Comparing natural selection vs genetic drift as mechanisms (population size effects, allele frequency changes, role of fitness vs randomness).
      NOT L4: Applying supply/demand to predict a shortage (that is L3). Explaining ONE isolated concept = L2.
      IMPORTANT — closely related principles count as L4 if the student explains multiple sub-points: e.g., explaining Newton's 3rd Law + conservation of momentum TOGETHER with WHY no external medium is needed + WHY the rocket carries its own oxidizer = L4 (multiple interacting sub-components addressed). The test is not "how many named laws" but "how many distinct sub-points are explained in the analysis".
   5=Evaluate: Uses analysis to reach a VERDICT — tells you WHAT IS BETTER or WHAT TO USE for specific conditions.
      DECISION RULE: if the answer's conclusion answers "which one should I use and when?", it is L5.
      Language strength doesn't matter: "might be preferred", "is often better", "makes it ideal" are all evaluative.
      Key patterns (any one = L5): "X is preferred for [condition]", "therefore for [use-case] use X", "X makes it [un]suitable for [scenario]"
   6=Create: Proposes a novel design, algorithm, proof technique, or approach not in standard literature.
${mathNote}

2. SOLO TAXONOMY (1-5):
   1=Prestructural: No relevant understanding.
   2=Unistructural: One relevant concept correctly identified.
   3=Multistructural: Several concepts listed but not connected.
   4=Relational: Multiple concepts integrated — shows HOW they relate.
   5=Extended Abstract: Generalises beyond the specific topic.

CALIBRATION RULES:
- Do NOT award L4 just because the student explains a mechanism — L2 can explain mechanisms.
- Do NOT award L4 for applying a single framework to predict an outcome — that is L3.
- ONLY award L4 when you see MULTIPLE interacting components deconstructed, or MULTIPLE alternatives compared mechanistically.
- Do NOT upgrade from L2 because language sounds sophisticated or the explanation is fluent.`

  const user = `QUESTION: ${question}

STUDENT ANSWER: ${answer}

CONCEPT GRAPH EVIDENCE:
- Concepts found: ${numConcepts} (${conceptList})
- Relationships: ${numRels}
- Isolated concepts: ${isolatedCount}

Return ONLY valid JSON:
{"blooms":{"level":1,"label":"Remember","reasoning":"one sentence","confidence":0.9},"solo":{"level":1,"label":"Prestructural","reasoning":"one sentence","confidence":0.9}}`

  return { system, user }
}

function makeScoringPrompt(question, answer, bloomLabel, bloomLevel, soloLabel, soloLevel, numConcepts, numMisc, critical, isMath) {
  const mathNote = isMath ? `
MATH SCORING NOTE: Award credit for correct mathematical steps even if the final answer is wrong. Penalise for wrong formulas or invalid proof steps (treat as critical misconceptions).` : ''

  return `QUESTION: ${question}

STUDENT ANSWER: ${answer}

ASSESSMENT:
- Bloom's: ${bloomLabel} (L${bloomLevel}/6)
- SOLO: ${soloLabel} (L${soloLevel}/5)
- Concepts: ${numConcepts} | Misconceptions: ${numMisc} (${critical} critical)

SCORING RUBRIC (Bloom's level sets the ceiling):
- L1 Remember: 0.10–0.32 (0.5–1.6/5)
- L2 Understand: 0.28–0.58 (1.4–2.9/5)
- L3 Apply: 0.48–0.68 (2.4–3.4/5)
- L4 Analyze: 0.62–0.88 (3.1–4.4/5)
- L5 Evaluate: 0.82–1.00 (4.1–5.0/5)
- L6 Create: 0.88–1.00 (4.4–5.0/5)
${mathNote}

Return ONLY valid JSON: {"score":0.0-1.0,"rationale":"one sentence","missing":"what's absent or null"}`
}

// ─── Score bands ──────────────────────────────────────────────────────────────
const bloomsBand = { 1:[0.10,0.32], 2:[0.28,0.58], 3:[0.48,0.68], 4:[0.62,0.88], 5:[0.82,1.00], 6:[0.88,1.00] }

// ─── Grade one scenario ───────────────────────────────────────────────────────
async function grade(scenario) {
  const { question, student_answer: answer, domain } = scenario
  const isMath = domain === 'math'

  // Stage 1: concept extraction
  const { system: extSys, user: extUser } = makeExtractionPrompts(domain, question, answer)
  const extractResp = await callGemini(extSys, extUser, 4096, true)
  let conceptGraph = {}
  try {
    const raw = extractJson(extractResp).trimStart()
    conceptGraph = JSON.parse(raw.startsWith('{') ? raw : `{${raw}}`)
  } catch { /* silent fallback */ }

  const concepts = conceptGraph.concepts || []
  const relationships = conceptGraph.relationships || []
  const numConcepts = concepts.length
  const conceptList = concepts.map(c => c.id || '?').join(', ')
  const connected = new Set()
  relationships.forEach(r => { connected.add(r.s||''); connected.add(r.t||'') })
  const isolated = concepts.filter(c => !connected.has(c.id||'')).length
  const incorrectConcepts = concepts.filter(c => c.ok === false)
  const incorrectRels = relationships.filter(r => r.ok === false)

  // Stage 2+3 in parallel: depth + misconceptions
  const { system: depSys, user: depUser } = makeDepthPrompts(
    domain, question, answer, numConcepts, conceptList, relationships.length, isolated, isMath)

  const miscUser = `QUESTION: ${question}
STUDENT ANSWER: ${answer}

EXTRACTION ERRORS: ${[...incorrectConcepts.map(c => c.id), ...incorrectRels.map(r => `${r.s}→${r.t}`)].join(', ') || 'None'}

Scan for factual errors/misconceptions. Return ONLY: {"misconceptions":[{"type":"...","severity":"critical|moderate|minor","explanation":"..."}],"summary":"..."}`
  const miscSys = `You are an expert ${isMath ? 'Mathematics' : domain} educator checking for factual errors and misconceptions.`

  const [depthResp, miscResp] = await Promise.all([
    callGemini(depSys, depUser, 1024, true),
    callGemini(miscSys, miscUser, 1024, true),
  ])

  let depthResult = {}
  try { depthResult = JSON.parse(extractJson(depthResp)) } catch { /* fallback */ }
  const blooms = depthResult.blooms || { level: 1, label: 'Remember' }
  const solo = depthResult.solo || { level: 1, label: 'Prestructural' }

  let miscResult = { misconceptions: [] }
  try { miscResult = JSON.parse(extractJson(miscResp)) } catch { /* fallback */ }
  const miscList = miscResult.misconceptions || []
  const numMisc = miscList.length
  const critical = miscList.filter(m => m.severity === 'critical').length

  // Stage 4: scoring
  const scoringPrompt = makeScoringPrompt(
    question, answer, blooms.label, blooms.level,
    solo.label, solo.level, numConcepts, numMisc, critical, isMath)
  const scoreResp = await callGemini(
    'You are an expert educator. Return only valid JSON.', scoringPrompt, 512, true)

  let overallScore = 0
  let rationale = ''
  try {
    const sr = JSON.parse(extractJson(scoreResp))
    const rawScore = Math.max(0, Math.min(1, parseFloat(sr.score) || 0))
    const [bMin, bMax] = bloomsBand[blooms.level || 1] ?? [0.10, 1.00]
    const penalty = critical * 0.08 + Math.max(0, numMisc - critical) * 0.03
    overallScore = Math.max(bMin, Math.min(bMax - penalty, rawScore))
    rationale = sr.rationale || ''
  } catch { /* fallback = 0 */ }

  return {
    score: overallScore,
    displayScore: parseFloat((overallScore * 5).toFixed(2)),
    bloomLevel: blooms.level,
    bloomLabel: blooms.label,
    bloomReasoning: blooms.reasoning || '',
    soloLevel: solo.level,
    soloLabel: solo.label,
    numConcepts,
    numMisc,
    critical,
    rationale,
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────
async function run() {
  const scenarios = JSON.parse(readFileSync(SCENARIOS_FILE, 'utf8'))
  const icon = p => p ? '✓' : '✗'
  const results = []

  console.log('╔══════════════════════════════════════════════════════════════╗')
  console.log('║  ConceptGrade Multi-Domain Stress Test                       ║')
  console.log(`╚══════════════════════════════════════════════════════════════╝\n`)

  for (let i = 0; i < scenarios.length; i++) {
    const s = scenarios[i]
    const words = s.student_answer.split(' ').length
    console.log(`━━━ [${i+1}/${scenarios.length}] ${s.scenario_id} | ${s.domain.toUpperCase()} L${s.level} | ${words}w ━━━`)
    console.log(`  Expected: ${s.expected_score_min}–${s.expected_score_max}/5  |  Bloom L${s.expected_bloom_level}`)

    let result
    try {
      result = await grade(s)
    } catch (e) {
      console.log(`  ERROR: ${e.message}`)
      results.push({ ...s, error: e.message, pass: false })
      if (i < scenarios.length - 1) await new Promise(r => setTimeout(r, PAUSE_MS))
      continue
    }

    const inRange = result.displayScore >= s.expected_score_min && result.displayScore <= s.expected_score_max
    const bloomMatch = result.bloomLevel === s.expected_bloom_level
    const pass = inRange && bloomMatch

    console.log(`  Score:    ${result.displayScore}/5  [${s.expected_score_min}–${s.expected_score_max}]  ${icon(inRange)}`)
    console.log(`  Bloom's:  L${result.bloomLevel} ${result.bloomLabel}  (expected L${s.expected_bloom_level})  ${icon(bloomMatch)}`)
    console.log(`  SOLO:     L${result.soloLevel} ${result.soloLabel}  |  Concepts: ${result.numConcepts}  |  Misc: ${result.numMisc} (${result.critical} crit)`)
    if (result.rationale) console.log(`  Rationale: ${result.rationale.substring(0, 130)}`)
    if (result.bloomReasoning) console.log(`  CoT: ${result.bloomReasoning.substring(0, 130)}`)
    console.log(`  → ${pass ? 'PASS' : 'FAIL'}`)

    results.push({ ...s, actual_score: result.displayScore, actual_bloom: result.bloomLevel,
      actual_bloom_label: result.bloomLabel, num_concepts: result.numConcepts,
      num_misc: result.numMisc, critical: result.critical,
      score_in_range: inRange, bloom_match: bloomMatch, pass })

    if (i < scenarios.length - 1) await new Promise(r => setTimeout(r, PAUSE_MS))
  }

  // Summary
  const passed = results.filter(r => r.pass).length
  const pct = ((passed / results.length) * 100).toFixed(0)
  console.log('\n╔═══════════════════════════════════════════════════════════════════════╗')
  console.log('║  FINAL SUMMARY                                                        ║')
  console.log('╚═══════════════════════════════════════════════════════════════════════╝')
  console.log('Scenario               Domain  Lvl  Expected    Got      Exp→Got   S  B  Overall')
  console.log('─'.repeat(85))

  for (const r of results) {
    if (r.error) { console.log(`${r.scenario_id.padEnd(23)}${r.domain.padEnd(8)}L${r.level}  ERROR`); continue }
    const s = icon(r.score_in_range), b = icon(r.bloom_match), p = r.pass ? '✓ PASS' : '✗ FAIL'
    console.log(`${r.scenario_id.padEnd(23)}${r.domain.padEnd(8)}L${r.level}  ${(r.expected_score_min+'-'+r.expected_score_max).padEnd(12)}${String(r.actual_score+'/5').padEnd(9)}L${r.expected_bloom_level}→L${r.actual_bloom}        ${s}  ${b}  ${p}`)
  }
  console.log('─'.repeat(85))
  console.log(`\nResult: ${passed}/${results.length} PASSED (${pct}%)`)

  // By domain
  const byDomain = {}
  for (const r of results) {
    byDomain[r.domain] = byDomain[r.domain] || { pass: 0, total: 0 }
    byDomain[r.domain].total++
    if (r.pass) byDomain[r.domain].pass++
  }
  console.log('\nBy domain:')
  for (const [d, v] of Object.entries(byDomain)) {
    console.log(`  ${d.padEnd(12)}: ${v.pass}/${v.total} (${Math.round(v.pass/v.total*100)}%)`)
  }

  writeFileSync('/tmp/multidomain_results.json', JSON.stringify(results, null, 2))
  console.log('\nFull results saved to /tmp/multidomain_results.json')
}

run().catch(e => { console.error('Fatal:', e); process.exit(1) })
