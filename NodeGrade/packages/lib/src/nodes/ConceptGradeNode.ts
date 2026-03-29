/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

// ── CS Misconception Taxonomy (mirrors MisconceptionDetectorNode) ──────────
const CS_MISCONCEPTION_TAXONOMY: Record<string, { description: string; common_claim: string; correct: string; severity: string }> = {
  'DS-STACK-01': { description: 'Confusing LIFO (stack) with FIFO (queue)', common_claim: 'A stack follows First In First Out order', correct: 'A stack follows LIFO; a queue follows FIFO', severity: 'critical' },
  'DS-STACK-02': { description: 'Thinking stacks can only be implemented with arrays', common_claim: 'Stacks must use arrays as the underlying storage', correct: 'Stacks can be implemented with either arrays or linked lists', severity: 'minor' },
  'DS-LINK-01': { description: 'Confusing array indices with pointer-based access', common_claim: 'You can access linked list elements by index in O(1)', correct: 'Linked list access requires O(n) traversal; only arrays support O(1) index access', severity: 'critical' },
  'DS-LINK-02': { description: 'Believing linked lists use contiguous memory', common_claim: 'Linked list nodes are stored next to each other in memory', correct: 'Linked list nodes are dynamically allocated and can be anywhere in memory', severity: 'critical' },
  'DS-TREE-01': { description: 'Assuming all binary trees are binary search trees', common_claim: 'Any binary tree has the ordered property', correct: 'Only BSTs maintain the ordering property; a general binary tree has no ordering constraint', severity: 'critical' },
  'DS-HASH-01': { description: 'Assuming hash tables never have worst-case O(n)', common_claim: 'Hash table operations are always O(1)', correct: 'Hash table operations are O(1) average; worst case with many collisions is O(n)', severity: 'moderate' },
  'DS-SORT-01': { description: 'Believing quicksort is always faster than merge sort', common_claim: 'Quick sort is always the fastest sorting algorithm', correct: 'Quick sort average is O(n log n) but worst case is O(n²); merge sort guarantees O(n log n)', severity: 'moderate' },
}

/**
 * ConceptGradeNode
 *
 * Full ConceptGrade assessment pipeline in a single node.
 * Orchestrates all 5 layers: KG → Extraction → Comparison →
 * Cognitive Depth → Misconception Detection.
 *
 * Part of the Concept-Aware Assessment Framework (Paper 3).
 *
 * Inputs:
 *   - student_answer (string): The student's free-text response
 *   - question (string): The assessment question
 *
 * Outputs:
 *   - overall_score (string): 0-1 composite score
 *   - depth_category (string): surface/moderate/deep/expert
 *   - blooms_label (string): Bloom's taxonomy level
 *   - solo_label (string): SOLO taxonomy level
 *   - num_misconceptions (string): Count of misconceptions
 *   - full_report (string): Complete JSON assessment report
 */
export class ConceptGradeNode extends LGraphNode {
  env: Record<string, unknown>
  properties: {
    overall_score: number
    depth_category: string
    blooms_label: string
    solo_label: string
  }

  constructor() {
    super()
    this.addIn('string', 'student answer')
    this.addIn('string', 'question')
    this.addIn('string', 'domain')          // optional: e.g. "physics", "civil engineering"
    this.addOut('string', 'overall score')
    this.addOut('string', 'depth category')
    this.addOut('string', 'blooms label')
    this.addOut('string', 'solo label')
    this.addOut('string', 'num misconceptions')
    this.addOut('string', 'full report (JSON)')
    this.properties = {
      overall_score: 0,
      depth_category: 'surface',
      blooms_label: '',
      solo_label: ''
    }
    this.title = 'ConceptGrade'
    this.serialize_widgets = true
    this.env = {}
  }

  static title = 'ConceptGrade'
  static path = 'concept-aware/conceptgrade'
  static getPath(): string {
    return ConceptGradeNode.path
  }

  async init(_env: Record<string, unknown>) {
    this.env = _env
  }

  async onExecute() {
    if (typeof window !== 'undefined') {
      throw new Error('ConceptGradeNode can only execute on the backend')
    }

    const studentAnswer = this.getInputData<string>(0) || ''
    const question = this.getInputData<string>(1) || ''
    const domain = (this.getInputData<string>(2) || '').trim() || 'general'

    if (!studentAnswer.trim()) {
      this.setOutputData(0, '0')
      this.setOutputData(1, 'surface')
      this.setOutputData(2, 'N/A')
      this.setOutputData(3, 'N/A')
      this.setOutputData(4, '0')
      this.setOutputData(5, '{}')
      return
    }

    const geminiApiKey = this.env.GEMINI_API_KEY as string | undefined
    const workerUrl = (this.env.MODEL_WORKER_URL as string) ?? 'https://api.groq.com/openai'
    const bearerToken = this.env.BEARER_TOKEN as string | undefined
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (bearerToken) headers['Authorization'] = `Bearer ${bearerToken}`

    const llm = (prompt: string, system: string, maxTokens = 1024, jsonMode = false): Promise<string> =>
      geminiApiKey
        ? this.callGemini(geminiApiKey, prompt, system, maxTokens, jsonMode)
        : this.callLLM(workerUrl, headers, prompt, system, maxTokens)

    const emitProgress = (pct: number, stage: string) => {
      this.emitEventCallback?.({ eventName: 'percentageUpdated', payload: pct })
      this.emitEventCallback?.({ eventName: 'outputSet', payload: { uniqueId: 'grading-stage', type: 'text', label: 'grading-stage', value: stage } })
    }

    // Truncate for extraction only — concept labels need ~2000 chars of text,
    // not the full answer. Stages 2 & 4 always receive the full studentAnswer.
    const answerForExtraction = studentAnswer.length > 3000
      ? studentAnswer.substring(0, 3000) + '\n[...answer truncated for concept extraction...]'
      : studentAnswer

    // Run multi-stage pipeline via sequential LLM calls
    try {
      // Stage 1: Concept Extraction — domain-adaptive relationship types
      // Relationship vocabulary varies by domain to improve concept graph fidelity
      const domainLower = domain.toLowerCase()
      const isMath = domainLower.includes('math')
      const isCS = domainLower.includes('computer') || domainLower.includes('software') || domainLower.includes('cs')
      const isEngineering = domainLower.includes('engineer') || domainLower.includes('mechanic') ||
        domainLower.includes('civil') || domainLower.includes('electrical') || domainLower.includes('chemical') ||
        domainLower.includes('aerospace') || domainLower.includes('biomedical') || domainLower.includes('robotic') ||
        domainLower.includes('environmental') || domainLower.includes('industrial')

      const relTypes = isMath
        ? 'uses, proves, derives, applies, defines, is_equivalent_to, is_step_of, is_special_case_of'
        : isCS
        ? 'is_a, has_part, prerequisite_for, implements, uses, has_property, has_complexity, contrasts_with'
        : isEngineering
        ? 'is_a, has_part, causes, leads_to, uses, has_property, contrasts_with, requires, produces, governs'
        : 'is_a, has_part, causes, leads_to, uses, contrasts_with, has_property, explains, supports, challenges'

      const extractionSystemPrompt = `You are an expert ${domain} educator analyzing student answers.
Extract domain concepts and relationships from the student's response using compact JSON.
Keep concept_id values short (1-3 words, snake_case). Limit to at most 12 concepts and 10 relationships.
Relationship types: ${relTypes}`

      const extractionPrompt = `QUESTION: ${question}

STUDENT ANSWER: ${answerForExtraction}

Return compact JSON (no whitespace):
{"concepts":[{"id":"name","ok":true}],"relationships":[{"s":"src","t":"tgt","r":"type","ok":true}],"depth":"surface|moderate|deep"}`

      emitProgress(10, 'Extracting concepts...')
      const extractResp = await llm(extractionPrompt, extractionSystemPrompt, 4096, true)
      emitProgress(30, 'Classifying depth & detecting misconceptions...')

      let conceptGraph: any = {}
      try {
        const raw = this.extractJson(extractResp).trimStart()
        const jsonStr = raw.startsWith('{') ? raw : `{${raw}}`
        conceptGraph = JSON.parse(jsonStr)
      } catch (e) {
        console.error('[ConceptGrade] concept extraction parse failed, raw:', extractResp.substring(0, 200))
      }

      const concepts = conceptGraph.concepts || []
      const relationships = conceptGraph.relationships || []
      const numConcepts = concepts.length
      const numRelationships = relationships.length
      const incorrectConcepts = concepts.filter((c: any) => c.ok === false || c.is_correct === false)
      const incorrectRelationships = relationships.filter((r: any) => r.ok === false || r.is_correct === false)

      // Stage 2: Cognitive Depth Classification — evidence-based + Chain-of-Thought
      const conceptList = concepts.map((c: any) => c.id || c.concept_id || '?').join(', ')
      const connectedConcepts = new Set<string>()
      for (const r of relationships) {
        connectedConcepts.add(r.s || r.source || '')
        connectedConcepts.add(r.t || r.target || '')
      }
      const isolatedCount = concepts.filter((c: any) => !connectedConcepts.has(c.id || c.concept_id || '')).length

      const depthSystemPrompt = `You are an expert educational assessment researcher. Classify this student response in the domain of ${domain} along TWO taxonomies simultaneously using Chain-of-Thought reasoning and the provided concept graph evidence.

⚠ CRITICAL RULE — COGNITIVE LEVEL ≠ CORRECTNESS:
Bloom's level reflects the COGNITIVE OPERATION the student ATTEMPTED, not whether the answer is correct.
DO NOT downgrade the Bloom's level because of factual errors. DO NOT upgrade the level because the answer sounds complex but only lists facts.

1. BLOOM'S REVISED TAXONOMY (1-6):
   1=Remember: Recalls a fact, definition, or formula with no explanation beyond stating it.
      Examples: stating Newton's First Law verbatim; defining "opportunity cost"; listing DNA bases; stating KCL.

   2=Understand: Explains in own words, paraphrases, gives examples. Uses ONE concept to explain ONE phenomenon.
      Examples across domains:
        • "Metal feels colder because thermal conductivity transfers heat away faster." (ONE concept, ONE cause-effect)
        • "Vaccines train the immune system by introducing antigens that trigger memory cell production." (biology)
        • "Recursion works by having a function call itself with a smaller sub-problem until a base case stops it." (CS)
      Counter-example: A brief mention of trade-offs without mechanistic detail is STILL L2.

   3=Apply: Takes an established principle, law, or framework and uses it to PREDICT or SOLVE a specific new scenario. Shows working steps.
      Examples across domains:
        • "Using F=ma: a=24/4=6 m/s²." (physics — applying formula)
        • "A price ceiling below equilibrium → consumers demand more, producers supply less → shortage." (economics)
        • "The camouflage mutation raises survival rate → allele frequency shifts over generations." (biology — applying natural selection)
        • "BST: 6<10 go left, 6>5 go right, 6<7 → insert as left child of 7." (CS — step-by-step application)
        • "Using CSTR design equation: V = F_A0·X / (-r_A) = 100·0.8 / (0.5·0.4) = 400 L." (chemical engineering)
      Key: applying a known framework to predict or calculate for a specific scenario = L3.

   4=Analyze: Deconstructs a COMPLEX system into MULTIPLE interacting components, OR compares MULTIPLE alternatives with mechanistic evidence of WHY they differ.
      Examples across domains:
        • Refrigerator cycle: compressor→condenser→expansion valve→evaporator — all components and interactions. (engineering)
        • DFS vs BFS: space O(h) vs O(w), why BFS guarantees shortest paths, when each is preferred. (CS)
        • Industrial Revolution: coal+iron, agricultural release of labour, capital markets, colonial demand — all interacting causes. (history)
        • BJT transistor: minority carrier injection + thin-base design + NHEJ/HDR repair pathways. (EE/biomedical)
      IMPORTANT — closely related principles still count as L4 when the student covers MULTIPLE distinct sub-points:
        e.g., Newton's 3rd Law + momentum conservation + WHY no external medium is needed + self-contained oxidiser = L4.
        The test is "how many DISTINCT sub-points are analysed", not "how many named laws are cited".
      Counter-examples (NOT L4): explaining ONE concept for ONE phenomenon = L2. Applying supply/demand to predict a single outcome = L3.

   5=Evaluate: Uses analysis to reach a VERDICT — tells you WHAT IS BETTER or WHAT TO USE in specific conditions.
      DECISION RULE: if the conclusion answers "which one should I use and when?", it is L5.
      L4 answers "how does it work?" — L5 answers "which is better and for what?"
      Language strength does NOT matter: "might be preferred", "is often a better choice", "makes it ideal" are ALL evaluative.
      Key patterns (any one is sufficient): "X preferred for [condition A]; Y preferred for [condition B]"; "Therefore use X for Y"; "X is unsuitable for Z because…"

   6=Create: Proposes a NOVEL design, algorithm, proof technique, methodology, or system not in standard literature.
      Note for mathematics: deriving a known result from first principles = L4. Proposing a genuinely new proof strategy = L6.

2. SOLO TAXONOMY (1-5):
   1=Prestructural: No relevant understanding.
   2=Unistructural: One relevant concept correctly identified.
   3=Multistructural: Several concepts listed but not connected — parallel, not integrated.
   4=Relational: Multiple concepts integrated — shows HOW they relate.
   5=Extended Abstract: Generalises beyond the specific topic or question domain.

CALIBRATION RULES:
- Do NOT award L4 just because the student explains a mechanism — L2 explains mechanisms using ONE concept.
- Do NOT award L4 for applying a single framework to predict or calculate — that is L3.
- ONLY award L4 when you see MULTIPLE interacting components deconstructed, or MULTIPLE alternatives compared mechanistically.
- UPGRADE from L4 to L5 if the student makes design/selection recommendations tied to specific criteria, even with hedged language.
- Do not DOWNGRADE from L3/L4 because of misconceptions — classify the INTENDED cognitive operation.
- Do not UPGRADE from L2 because the language sounds sophisticated — look for the actual cognitive operation performed.`

      const depthPrompt = `QUESTION: ${question}

STUDENT ANSWER: ${studentAnswer}

CONCEPT GRAPH EVIDENCE:
- Concepts found: ${numConcepts} (${conceptList})
- Relationships: ${numRelationships}
- Isolated concepts (no connections): ${isolatedCount}
- KG depth assessment: ${conceptGraph.overall_depth || 'not assessed'}

Return ONLY valid JSON:
{
  "blooms": {
    "level": 1-6,
    "label": "Remember|Understand|Apply|Analyze|Evaluate|Create",
    "reasoning": "brief chain-of-thought",
    "confidence": 0.0-1.0
  },
  "solo": {
    "level": 1-5,
    "label": "Prestructural|Unistructural|Multistructural|Relational|Extended Abstract",
    "reasoning": "brief chain-of-thought",
    "confidence": 0.0-1.0
  }
}`

      // Build stage 3 inputs before parallel launch
      const allIncorrect = [...incorrectConcepts, ...incorrectRelationships]
      const studentConceptSet = new Set(concepts.map((c: any) => (c.id || c.concept_id || '').toLowerCase()))
      const taxonomyMatches = Object.entries(CS_MISCONCEPTION_TAXONOMY)
        .filter(([, tax]) => tax.description.toLowerCase().split(' ').some(w => w.length > 4 && studentConceptSet.has(w)))
      const taxonomyStr = taxonomyMatches.length > 0
        ? taxonomyMatches.map(([id, tax]) =>
            `- ${id}: ${tax.description}\n  Common claim: "${tax.common_claim}"\n  Correct: "${tax.correct}" (${tax.severity})`
          ).join('\n')
        : 'No direct taxonomy matches — analyse as novel misconceptions if any exist.'
      const extractedErrors = allIncorrect.map((r: any) =>
        `- ${r.id || r.concept_id || r.s || r.source || '?'} → ${r.t || r.target || ''} (${r.r || r.relation_type || 'concept error'}): marked incorrect`
      ).join('\n')

      const miscSystemPrompt = `You are an expert ${domain} educator analyzing student answers for factual errors and misconceptions.
Scan the FULL student answer for factual errors and misconceptions relevant to ${domain}. Do NOT just report extraction errors — actively check the answer for:
- Wrong factual claims about domain concepts
- Confusing related concepts or properties
- Wrong assertions about how things work
- Overgeneralizations and unsupported absolute claims

If the answer contains NO factual errors, return empty misconceptions array.
For each misconception found:
1. Type: systematic|isolated|knowledge_gap|conflation|overgeneralization|undergeneralization
2. Severity: critical (fundamentally wrong core concept), moderate (incorrect detail), minor (imprecise)
3. Match to taxonomy ID if applicable
4. Clear explanation and remediation hint`

      const miscPrompt = `QUESTION: ${question}
STUDENT ANSWER: ${studentAnswer}

EXTRACTION-FLAGGED ERRORS (may be empty):
${extractedErrors || 'None flagged by extraction.'}

RELEVANT MISCONCEPTION TAXONOMY:
${taxonomyStr}

Scan the full answer for ANY factual misconceptions. Return ONLY valid JSON:
{"misconceptions":[{"taxonomy_match":"DS-XXX-NN or novel","type":"systematic|isolated|knowledge_gap|conflation|overgeneralization|undergeneralization","severity":"critical|moderate|minor","explanation":"...","remediation_hint":"..."}],"summary":"..."}`

      // ── Stages 2 & 3 run IN PARALLEL (both depend only on Stage 1 output) ──
      const [depthResp, miscResp] = await Promise.all([
        llm(depthPrompt, depthSystemPrompt, 2048, true),   // jsonMode; reasoning can be long
        llm(miscPrompt, miscSystemPrompt, 1024, true),     // jsonMode avoids fence issues
      ])
      emitProgress(70, 'Calculating final score...')

      let depthResult: any = {}
      try {
        const depthJson = this.extractJson(depthResp)
        depthResult = JSON.parse(depthJson)
      } catch (e) {
        console.error('[ConceptGrade] depth parse failed. Error:', String(e).substring(0, 100))
        console.error('[ConceptGrade] depth raw (first 500):', depthResp.substring(0, 500))
      }

      const blooms = depthResult.blooms || { level: 1, label: 'Remember' }
      const solo = depthResult.solo || { level: 1, label: 'Prestructural' }
      console.log(`[ConceptGrade] depth: Blooms L${blooms.level} ${blooms.label}, SOLO L${solo.level} ${solo.label}`)

      let misconceptions: any = { total: 0, misconceptions: [] }
      try { misconceptions = JSON.parse(this.extractJson(miscResp)) } catch { /* empty */ }

      const miscList = misconceptions.misconceptions || []
      const numMisc = miscList.length
      const critical = miscList.filter((m: any) => m.severity === 'critical').length
      // Enrich conceptGraph with relationship data for report
      conceptGraph.relationships = relationships

      // Stage 4: Holistic LLM scoring — Bloom's/SOLO level sets the score band ceiling
      const scoringPrompt = `You are an expert ${domain} educator grading a student answer. Score it from 0.0 to 1.0 (where 1.0 = 5/5).

QUESTION: ${question}

STUDENT ANSWER:
${studentAnswer}

AUTOMATED ASSESSMENT EVIDENCE:
- Bloom's Taxonomy: ${blooms.label} (Level ${blooms.level}/6)
- SOLO Taxonomy: ${solo.label} (Level ${solo.level}/5)
- Concepts identified: ${numConcepts}
- Misconceptions: ${numMisc} total, ${critical} critical

SCORING RUBRIC — the Bloom's level sets the CEILING for the score band:
- Bloom's L1 (Remember) / SOLO L1-L2: 0.10–0.30. Even if factually correct, recall alone earns at most 1.5/5.
- Bloom's L2 (Understand) / SOLO L2-L3: 0.30–0.55. Clear explanation with basic examples earns ~2.5/5 at best.
- Bloom's L3 (Apply) / SOLO L3: 0.50–0.65. Correct application of knowledge to a context.
- Bloom's L4 (Analyze) / SOLO L3-L4: 0.65–0.85. Detailed deconstruction of mechanisms and trade-offs.
- Bloom's L5 (Evaluate) / SOLO L4-L5: 0.85–1.00. Justified critique of design choices; thorough and accurate.
- Bloom's L6 (Create) / SOLO L5: 0.90–1.00 ONLY IF the novel design also answers the question asked. If the answer proposes novel ideas but ignores the question's core requirements, score within L4 range.

IMPORTANT:
- A complete and accurate L2 answer is worth ~2.5/5 (0.50), NOT 4–5/5. Do not award high scores purely for accuracy if depth is shallow.
- Missing elements from the question reduce the score within the band.
- Critical misconceptions reduce the score by 0.15–0.30.

Return ONLY valid JSON: {"score": 0.0-1.0, "rationale": "one sentence reason", "missing": "what is absent or null if nothing significant"}`

      // Bloom's level → score band [min, max] (slightly widened to reduce boundary brittleness)
      const bloomsBand: Record<number, [number, number]> = {
        1: [0.10, 0.32],  // 0.5-1.6/5
        2: [0.28, 0.58],  // 1.4-2.9/5
        3: [0.48, 0.68],  // 2.4-3.4/5
        4: [0.62, 0.88],  // 3.1-4.4/5
        5: [0.82, 1.00],  // 4.1-5.0/5
        6: [0.88, 1.00],  // 4.4-5.0/5
      }
      const [bandMin, bandMax] = bloomsBand[blooms.level || 1] ?? [0.10, 1.00]
      // Apply misconception penalty: critical misconceptions reduce the band ceiling
      const miscPenalty = critical * 0.08 + Math.max(0, numMisc - critical) * 0.03
      const effectiveBandMax = Math.max(bandMin, bandMax - miscPenalty)

      let overallScore = 0
      let scoreRationale = ''
      let scoreMissing: string | null = null
      try {
        const scoreResp = await llm(scoringPrompt, `You are an expert ${domain} educator. Return only valid JSON.`, 512, true)
        const scoreResult = JSON.parse(this.extractJson(scoreResp))
        const rawScore = Math.max(0, Math.min(1, parseFloat(scoreResult.score) || 0))
        // Clamp to Bloom's band — deterministic enforcement with misconception penalty
        overallScore = Math.max(bandMin, Math.min(effectiveBandMax, rawScore))
        scoreRationale = scoreResult.rationale || ''
        scoreMissing = scoreResult.missing || null
      } catch {
        // Fallback to deterministic formula if LLM scoring fails
        const bloomsNorm = ((blooms.level || 1) - 1) / 5
        const soloNorm = ((solo.level || 1) - 1) / 4
        const miscPenalty = critical * 0.3 + (numMisc - critical) * 0.1
        overallScore = Math.max(bandMin, Math.min(bandMax,
          bloomsNorm * 0.35 + soloNorm * 0.35 + (1 - miscPenalty) * 0.3
        ))
      }

      // Depth category
      let depthCategory = 'surface'
      if (blooms.level >= 5 && solo.level >= 4 && critical === 0) depthCategory = 'expert'
      else if (blooms.level >= 4 && solo.level >= 3 && critical === 0) depthCategory = 'deep'
      else if (blooms.level >= 2 && solo.level >= 2) depthCategory = 'moderate'

      // Build full report
      const report = {
        concept_graph: conceptGraph,
        blooms,
        solo,
        misconceptions,
        overall_score: overallScore,
        depth_category: depthCategory,
        score_rationale: scoreRationale,
        score_missing: scoreMissing,
      }

      this.properties.overall_score = overallScore
      this.properties.depth_category = depthCategory
      this.properties.blooms_label = blooms.label || 'Remember'
      this.properties.solo_label = solo.label || 'Prestructural'

      this.setOutputData(0, overallScore.toFixed(3))
      this.setOutputData(1, depthCategory)
      this.setOutputData(2, blooms.label || 'Remember')
      this.setOutputData(3, solo.label || 'Prestructural')
      this.setOutputData(4, String(numMisc))
      emitProgress(100, 'Done')
      this.setOutputData(5, JSON.stringify(report))

    } catch (error) {
      console.error('ConceptGradeNode error:', error)
      this.setOutputData(0, '0')
      this.setOutputData(1, 'error')
      this.setOutputData(2, 'Error')
      this.setOutputData(3, 'Error')
      this.setOutputData(4, '0')
      this.setOutputData(5, JSON.stringify({ error: String(error) }))
    }
  }

  private async callLLM(
    workerUrl: string,
    headers: Record<string, string>,
    userContent: string,
    systemContent: string,
    maxTokens = 2048
  ): Promise<string> {
    const response = await fetch(workerUrl + '/v1/chat/completions', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: 'llama-3.3-70b-versatile',
        messages: [
          { role: 'system', content: systemContent },
          { role: 'user', content: userContent }
        ],
        temperature: 0.1,
        max_tokens: maxTokens
      })
    })
    if (!response.ok) throw new Error(`API error: ${response.status}`)
    const data: any = await response.json()
    return data.choices?.[0]?.message?.content || '{}'
  }

  private async callGemini(
    apiKey: string,
    userContent: string,
    systemContent: string,
    maxTokens = 2048,
    jsonMode = false
  ): Promise<string> {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`
    const generationConfig: any = {
      temperature: 0.1,
      maxOutputTokens: maxTokens,
      thinkingConfig: { thinkingBudget: 0 },  // disable thinking tokens so full budget goes to output
    }
    if (jsonMode) generationConfig.responseMimeType = 'application/json'
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: systemContent }] },
        contents: [{ parts: [{ text: userContent }] }],
        generationConfig
      })
    })
    if (!response.ok) {
      const err = await response.text()
      throw new Error(`Gemini API error ${response.status}: ${err.substring(0, 200)}`)
    }
    const data: any = await response.json()
    return data.candidates?.[0]?.content?.parts?.[0]?.text || '{}'
  }

  private extractJson(text: string): string {
    // Strip ALL markdown fences (opening and closing), anywhere in the text
    let cleaned = text
      .replace(/```(?:json)?\s*\n?/g, '')  // remove all opening fences
      .replace(/\n?```/g, '')               // remove all closing fences
      .trim()
    // Sanitize: fix literal newlines/tabs inside JSON string values
    cleaned = this.sanitizeJsonStrings(cleaned)
    // Find the outermost balanced {} block
    const start = cleaned.indexOf('{')
    if (start === -1) return cleaned.trim()
    let depth = 0
    let inString = false
    let escape = false
    for (let i = start; i < cleaned.length; i++) {
      const ch = cleaned[i]
      if (escape) { escape = false; continue }
      if (ch === '\\' && inString) { escape = true; continue }
      if (ch === '"') { inString = !inString; continue }
      if (inString) continue
      if (ch === '{') depth++
      else if (ch === '}') { depth--; if (depth === 0) return cleaned.substring(start, i + 1) }
    }
    // Truncated JSON — return what we have from start
    return cleaned.substring(start)
  }

  /** Replace literal control characters inside JSON string values so JSON.parse succeeds */
  private sanitizeJsonStrings(text: string): string {
    let result = ''
    let inString = false
    let escape = false
    for (let i = 0; i < text.length; i++) {
      const ch = text[i]
      if (escape) { escape = false; result += ch; continue }
      if (ch === '\\' && inString) { escape = true; result += ch; continue }
      if (ch === '"') { inString = !inString; result += ch; continue }
      if (inString) {
        if (ch === '\n') { result += '\\n'; continue }
        if (ch === '\r') { result += '\\r'; continue }
        if (ch === '\t') { result += '\\t'; continue }
      }
      result += ch
    }
    return result
  }

  static register() {
    LiteGraph.registerNodeType(ConceptGradeNode.path, ConceptGradeNode)
  }
}
