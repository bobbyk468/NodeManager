/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

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

    if (!studentAnswer.trim()) {
      this.setOutputData(0, '0')
      this.setOutputData(1, 'surface')
      this.setOutputData(2, 'N/A')
      this.setOutputData(3, 'N/A')
      this.setOutputData(4, '0')
      this.setOutputData(5, '{}')
      return
    }

    const workerUrl = (this.env.MODEL_WORKER_URL as string) ?? 'https://api.groq.com/openai'
    const bearerToken = this.env.BEARER_TOKEN as string | undefined
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (bearerToken) headers['Authorization'] = `Bearer ${bearerToken}`

    // Run multi-stage pipeline via sequential LLM calls
    try {
      // Stage 1: Concept Extraction
      const extractionPrompt = `You are a CS education expert. Extract concepts and relationships from this student answer about Data Structures.

QUESTION: ${question}
STUDENT ANSWER: ${studentAnswer}

Return ONLY valid JSON:
{
  "concepts": [{"concept_id": "id", "evidence": "quote from answer"}],
  "relationships": [{"source_id": "id", "target_id": "id", "relation_type": "type", "is_correct": true/false}],
  "overall_depth": "surface|moderate|deep"
}`

      const extractResp = await this.callLLM(workerUrl, headers, extractionPrompt,
        'Extract concepts and relationships from the student answer.')

      let conceptGraph: any = {}
      try { conceptGraph = JSON.parse(this.extractJson(extractResp)) } catch { /* empty */ }

      const concepts = conceptGraph.concepts || []
      const relationships = conceptGraph.relationships || []
      const numConcepts = concepts.length
      const numRels = relationships.length
      const incorrectRels = relationships.filter((r: any) => r.is_correct === false)

      // Stage 2: Cognitive Depth Classification (Bloom's + SOLO combined)
      const depthPrompt = `You are an educational assessment researcher. Classify this student response on BOTH Bloom's Revised Taxonomy (1-6) and SOLO Taxonomy (1-5).

QUESTION: ${question}
STUDENT ANSWER: ${studentAnswer}
EVIDENCE: ${numConcepts} concepts, ${numRels} relationships, ${incorrectRels.length} incorrect

Return ONLY valid JSON:
{
  "blooms": {"level": 1-6, "label": "Remember|Understand|Apply|Analyze|Evaluate|Create", "confidence": 0-1},
  "solo": {"level": 1-5, "label": "Prestructural|Unistructural|Multistructural|Relational|Extended Abstract", "confidence": 0-1}
}`

      const depthResp = await this.callLLM(workerUrl, headers, depthPrompt,
        'Classify cognitive depth on Bloom\'s and SOLO taxonomies.')

      let depthResult: any = {}
      try { depthResult = JSON.parse(this.extractJson(depthResp)) } catch { /* empty */ }

      const blooms = depthResult.blooms || { level: 1, label: 'Remember' }
      const solo = depthResult.solo || { level: 1, label: 'Prestructural' }

      // Stage 3: Misconception Analysis (only if incorrect relationships found)
      let misconceptions: any = { total: 0, misconceptions: [] }
      if (incorrectRels.length > 0) {
        const miscPrompt = `Analyze misconceptions in this CS student answer:

QUESTION: ${question}
STUDENT ANSWER: ${studentAnswer}
INCORRECT: ${JSON.stringify(incorrectRels.slice(0, 5))}

Return ONLY valid JSON:
{
  "misconceptions": [{"severity": "critical|moderate|minor", "explanation": "...", "remediation_hint": "..."}],
  "summary": "overall assessment"
}`

        const miscResp = await this.callLLM(workerUrl, headers, miscPrompt,
          'Analyze misconceptions in the student response.')
        try { misconceptions = JSON.parse(this.extractJson(miscResp)) } catch { /* empty */ }
      }

      const miscList = misconceptions.misconceptions || []
      const numMisc = miscList.length
      const critical = miscList.filter((m: any) => m.severity === 'critical').length

      // Compute composite score
      const bloomsNorm = ((blooms.level || 1) - 1) / 5
      const soloNorm = ((solo.level || 1) - 1) / 4
      const miscPenalty = critical * 0.3 + (numMisc - critical) * 0.1
      const overallScore = Math.max(0, Math.min(1,
        bloomsNorm * 0.35 + soloNorm * 0.35 + (1 - miscPenalty) * 0.3
      ))

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
    systemContent: string
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
        max_tokens: 2048
      })
    })
    if (!response.ok) throw new Error(`API error: ${response.status}`)
    const data: any = await response.json()
    return data.choices?.[0]?.message?.content || '{}'
  }

  private extractJson(text: string): string {
    const jsonMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/)
    if (jsonMatch) return jsonMatch[1].trim()
    const s = text.indexOf('{')
    const e = text.lastIndexOf('}')
    if (s !== -1 && e !== -1) return text.substring(s, e + 1)
    return text.trim()
  }

  static register() {
    LiteGraph.registerNodeType(ConceptGradeNode.path, ConceptGradeNode)
  }
}
