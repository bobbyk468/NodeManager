/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

/**
 * CognitiveDepthNode
 *
 * Dual-taxonomy cognitive depth classifier for student responses.
 * Classifies along both Bloom's Revised Taxonomy and SOLO Taxonomy
 * using Chain-of-Thought prompting with concept graph evidence.
 *
 * Part of the Concept-Aware Assessment Framework (Paper 2).
 *
 * Inputs:
 *   - student_answer (string): The student's free-text response
 *   - question (string): The assessment question
 *   - concept_graph (string): JSON from ConceptExtractorNode
 *   - comparison_result (string): JSON from KnowledgeGraphCompareNode
 *
 * Outputs:
 *   - blooms_level (string): 1-6 Bloom's level
 *   - blooms_label (string): Remember/Understand/Apply/Analyze/Evaluate/Create
 *   - solo_level (string): 1-5 SOLO level
 *   - solo_label (string): Prestructural/Unistructural/Multistructural/Relational/Extended Abstract
 *   - combined_report (string): JSON with both classifications + reasoning
 */
export class CognitiveDepthNode extends LGraphNode {
  env: Record<string, unknown>
  properties: {
    blooms_level: number
    blooms_label: string
    solo_level: number
    solo_label: string
  }

  constructor() {
    super()
    this.addIn('string', 'student answer')
    this.addIn('string', 'question')
    this.addIn('string', 'concept graph (JSON)')
    this.addIn('string', 'comparison result (JSON)')
    this.addOut('string', 'blooms level')
    this.addOut('string', 'blooms label')
    this.addOut('string', 'solo level')
    this.addOut('string', 'solo label')
    this.addOut('string', 'combined report (JSON)')
    this.properties = {
      blooms_level: 0,
      blooms_label: '',
      solo_level: 0,
      solo_label: ''
    }
    this.title = 'Cognitive Depth'
    this.serialize_widgets = true
    this.env = {}
  }

  static title = 'Cognitive Depth'
  static path = 'concept-aware/cognitive-depth'
  static getPath(): string {
    return CognitiveDepthNode.path
  }

  async init(_env: Record<string, unknown>) {
    this.env = _env
  }

  async onExecute() {
    if (typeof window !== 'undefined') {
      throw new Error('CognitiveDepthNode can only execute on the backend')
    }

    const studentAnswer = this.getInputData<string>(0) || ''
    const question = this.getInputData<string>(1) || ''
    const conceptGraphJson = this.getInputData<string>(2) || '{}'
    const comparisonResultJson = this.getInputData<string>(3) || '{}'

    if (!studentAnswer.trim()) {
      this.setOutputData(0, '0')
      this.setOutputData(1, 'N/A')
      this.setOutputData(2, '0')
      this.setOutputData(3, 'N/A')
      this.setOutputData(4, '{}')
      return
    }

    let conceptGraph: any = {}
    let comparisonResult: any = {}
    try {
      conceptGraph = JSON.parse(conceptGraphJson)
      comparisonResult = JSON.parse(comparisonResultJson)
    } catch { /* use defaults */ }

    // Extract evidence
    const concepts = conceptGraph.concepts || []
    const relationships = conceptGraph.relationships || []
    const scores = comparisonResult.scores || {}
    const numConcepts = concepts.length
    const conceptList = concepts.map((c: any) => c.concept_id || c.id || '?').slice(0, 15).join(', ')
    const numRels = relationships.length
    const integration = scores.integration_quality || 0
    const kgDepth = conceptGraph.overall_depth || 'not assessed'

    // Connected vs isolated concepts
    const connected = new Set<string>()
    for (const r of relationships) {
      connected.add(r.source_id || r.source || '')
      connected.add(r.target_id || r.target || '')
    }
    const isolated = concepts.filter((c: any) => !connected.has(c.concept_id || c.id || '')).length

    // Build combined prompt for both classifications
    const systemPrompt = `You are an expert educational assessment researcher. Classify this student response along TWO taxonomies simultaneously:

1. BLOOM'S REVISED TAXONOMY (1-6):
   1=Remember, 2=Understand, 3=Apply, 4=Analyze, 5=Evaluate, 6=Create

2. SOLO TAXONOMY (1-5):
   1=Prestructural (no understanding), 2=Unistructural (one concept),
   3=Multistructural (several concepts, unconnected), 4=Relational (integrated concepts),
   5=Extended Abstract (generalizes beyond question)

Use Chain-of-Thought reasoning and the concept graph evidence.`

    const userPrompt = `QUESTION: ${question}

STUDENT ANSWER: ${studentAnswer}

CONCEPT GRAPH EVIDENCE:
- Concepts found: ${numConcepts} (${conceptList})
- Relationships: ${numRels}
- Integration quality: ${(integration * 100).toFixed(0)}%
- Isolated concepts: ${isolated}
- KG depth assessment: ${kgDepth}

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
    "capacity": "none|one|several|many",
    "relating_operation": "none|identify|enumerate|relate|generalize",
    "reasoning": "brief chain-of-thought",
    "confidence": 0.0-1.0
  }
}`

    const workerUrl = (this.env.MODEL_WORKER_URL as string) ?? 'https://api.groq.com/openai'
    const bearerToken = this.env.BEARER_TOKEN as string | undefined

    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (bearerToken) headers['Authorization'] = `Bearer ${bearerToken}`

    try {
      const response = await fetch(workerUrl + '/v1/chat/completions', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: 'llama-3.3-70b-versatile',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: userPrompt }
          ],
          temperature: 0.1,
          max_tokens: 1500
        })
      })

      if (!response.ok) throw new Error(`API error: ${response.status}`)

      const data: any = await response.json()
      const content = data.choices?.[0]?.message?.content || '{}'

      let parsed: any = {}
      try {
        const jsonMatch = content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/)
        parsed = JSON.parse(jsonMatch ? jsonMatch[1].trim() : content.trim())
      } catch {
        const s = content.indexOf('{')
        const e = content.lastIndexOf('}')
        if (s !== -1 && e !== -1) parsed = JSON.parse(content.substring(s, e + 1))
      }

      const blooms = parsed.blooms || {}
      const solo = parsed.solo || {}

      const bloomsLevel = Math.max(1, Math.min(6, blooms.level || 1))
      const bloomsLabel = blooms.label || ['', 'Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'][bloomsLevel]
      const soloLevel = Math.max(1, Math.min(5, solo.level || 1))
      const soloLabel = solo.label || ['', 'Prestructural', 'Unistructural', 'Multistructural', 'Relational', 'Extended Abstract'][soloLevel]

      this.properties.blooms_level = bloomsLevel
      this.properties.blooms_label = bloomsLabel
      this.properties.solo_level = soloLevel
      this.properties.solo_label = soloLabel

      const report = {
        blooms: { level: bloomsLevel, label: bloomsLabel, ...blooms },
        solo: { level: soloLevel, label: soloLabel, ...solo },
        evidence: { num_concepts: numConcepts, num_relationships: numRels, integration, isolated, kg_depth: kgDepth }
      }

      this.setOutputData(0, String(bloomsLevel))
      this.setOutputData(1, bloomsLabel)
      this.setOutputData(2, String(soloLevel))
      this.setOutputData(3, soloLabel)
      this.setOutputData(4, JSON.stringify(report))

    } catch (error) {
      console.error('CognitiveDepthNode error:', error)
      // Heuristic fallback
      let bloomsLevel = 1
      let soloLevel = 1
      if (numConcepts >= 5 && numRels >= 4) { bloomsLevel = 4; soloLevel = 4 }
      else if (numConcepts >= 3 && numRels >= 2) { bloomsLevel = 3; soloLevel = 3 }
      else if (numConcepts >= 2) { bloomsLevel = 2; soloLevel = 3 }
      else if (numConcepts >= 1) { bloomsLevel = 1; soloLevel = 2 }

      const labels = ['', 'Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']
      const soloLabels = ['', 'Prestructural', 'Unistructural', 'Multistructural', 'Relational', 'Extended Abstract']

      this.setOutputData(0, String(bloomsLevel))
      this.setOutputData(1, labels[bloomsLevel])
      this.setOutputData(2, String(soloLevel))
      this.setOutputData(3, soloLabels[soloLevel])
      this.setOutputData(4, JSON.stringify({ error: String(error), fallback: true }))
    }
  }

  static register() {
    LiteGraph.registerNodeType(CognitiveDepthNode.path, CognitiveDepthNode)
  }
}
