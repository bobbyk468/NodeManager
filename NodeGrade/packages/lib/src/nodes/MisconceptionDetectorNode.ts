/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

/**
 * MisconceptionDetectorNode
 *
 * Detects and classifies misconceptions in student responses using
 * knowledge graph evidence and a curated CS misconception taxonomy.
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
 *   - num_misconceptions (string): Total count
 *   - severity_summary (string): "X critical, Y moderate, Z minor"
 *   - misconception_report (string): Full JSON report
 *   - feedback (string): Human-readable remediation feedback
 */
export class MisconceptionDetectorNode extends LGraphNode {
  env: Record<string, unknown>
  properties: {
    num_misconceptions: number
    severity_summary: string
  }

  constructor() {
    super()
    this.addIn('string', 'student answer')
    this.addIn('string', 'question')
    this.addIn('string', 'concept graph (JSON)')
    this.addIn('string', 'comparison result (JSON)')
    this.addOut('string', 'num misconceptions')
    this.addOut('string', 'severity summary')
    this.addOut('string', 'misconception report (JSON)')
    this.addOut('string', 'feedback')
    this.properties = {
      num_misconceptions: 0,
      severity_summary: ''
    }
    this.title = 'Misconception Detector'
    this.serialize_widgets = true
    this.env = {}
  }

  static title = 'Misconception Detector'
  static path = 'concept-aware/misconception-detector'
  static getPath(): string {
    return MisconceptionDetectorNode.path
  }

  async init(_env: Record<string, unknown>) {
    this.env = _env
  }

  async onExecute() {
    if (typeof window !== 'undefined') {
      throw new Error('MisconceptionDetectorNode can only execute on the backend')
    }

    const studentAnswer = this.getInputData<string>(0) || ''
    const question = this.getInputData<string>(1) || ''
    const conceptGraphJson = this.getInputData<string>(2) || '{}'
    const comparisonResultJson = this.getInputData<string>(3) || '{}'

    if (!studentAnswer.trim()) {
      this.setOutputData(0, '0')
      this.setOutputData(1, 'No misconceptions')
      this.setOutputData(2, '{}')
      this.setOutputData(3, 'No response to analyze.')
      return
    }

    let comparisonResult: any = {}
    let conceptGraph: any = {}
    try {
      comparisonResult = JSON.parse(comparisonResultJson)
      conceptGraph = JSON.parse(conceptGraphJson)
    } catch { /* use defaults */ }

    // Collect incorrect relationships from both sources
    const incorrectRels: any[] = []
    const studentConcepts = new Set<string>()

    // From comparison result
    const analysis = comparisonResult.analysis || comparisonResult
    for (const r of (analysis.incorrect_relationships || [])) {
      incorrectRels.push(r)
    }

    // From concept graph (extraction-time misconceptions)
    for (const c of (conceptGraph.concepts || [])) {
      studentConcepts.add(c.concept_id || c.id || '')
    }
    for (const r of (conceptGraph.relationships || [])) {
      if (r.is_correct === false) {
        incorrectRels.push({
          source: r.source_id || r.source || '',
          target: r.target_id || r.target || '',
          student_relation: r.relation_type || '',
          note: r.misconception_note || 'Flagged during extraction'
        })
      }
    }

    if (incorrectRels.length === 0) {
      this.properties.num_misconceptions = 0
      this.properties.severity_summary = 'No misconceptions detected'
      this.setOutputData(0, '0')
      this.setOutputData(1, 'No misconceptions detected')
      this.setOutputData(2, JSON.stringify({ total: 0, misconceptions: [] }))
      this.setOutputData(3, 'All demonstrated relationships appear correct.')
      return
    }

    // Build misconception analysis prompt
    const incorrectStr = incorrectRels.slice(0, 10).map((r: any) =>
      `- ${r.source || '?'} → ${r.target || '?'} (used: '${r.student_relation || '?'}'` +
      `${r.correct_relation ? `, correct: '${r.correct_relation}'` : ''}` +
      `)\n  Note: ${r.note || r.explanation || 'N/A'}`
    ).join('\n')

    const systemPrompt = `You are an expert CS educator analyzing student misconceptions about Data Structures and Algorithms.
For each incorrect relationship, determine:
1. Type: systematic (deep misunderstanding), isolated (one-off), knowledge_gap, conflation, overgeneralization, or undergeneralization
2. Severity: critical (blocks learning), moderate (causes problems), minor (imprecise)
3. Provide a clear explanation and remediation hint for the student.`

    const userPrompt = `QUESTION: ${question}
STUDENT ANSWER: ${studentAnswer}
INCORRECT RELATIONSHIPS:
${incorrectStr}

Return ONLY valid JSON:
{
  "misconceptions": [
    {
      "type": "systematic|isolated|knowledge_gap|conflation|overgeneralization|undergeneralization",
      "severity": "critical|moderate|minor",
      "source_concept": "id",
      "target_concept": "id",
      "student_claim": "what student said",
      "correct_understanding": "what is correct",
      "explanation": "clear explanation",
      "remediation_hint": "learning suggestion"
    }
  ],
  "summary": "overall assessment"
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
          max_tokens: 2048
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

      const misconceptions = parsed.misconceptions || []
      const critical = misconceptions.filter((m: any) => m.severity === 'critical').length
      const moderate = misconceptions.filter((m: any) => m.severity === 'moderate').length
      const minor = misconceptions.filter((m: any) => m.severity === 'minor').length
      const total = misconceptions.length

      const severitySummary = `${critical} critical, ${moderate} moderate, ${minor} minor`

      // Build feedback string
      const feedbackParts: string[] = []
      for (const m of misconceptions.slice(0, 5)) {
        feedbackParts.push(`[${(m.severity || 'moderate').toUpperCase()}] ${m.explanation || 'Review this concept.'}`)
        if (m.remediation_hint) feedbackParts.push(`  → ${m.remediation_hint}`)
      }
      const feedback = feedbackParts.join('\n') || 'No specific feedback.'

      this.properties.num_misconceptions = total
      this.properties.severity_summary = severitySummary

      this.setOutputData(0, String(total))
      this.setOutputData(1, severitySummary)
      this.setOutputData(2, JSON.stringify({
        total,
        by_severity: { critical, moderate, minor },
        misconceptions,
        summary: parsed.summary || ''
      }))
      this.setOutputData(3, feedback)

    } catch (error) {
      console.error('MisconceptionDetectorNode error:', error)
      const total = incorrectRels.length
      this.setOutputData(0, String(total))
      this.setOutputData(1, `${total} potential misconception(s) detected`)
      this.setOutputData(2, JSON.stringify({
        total,
        misconceptions: incorrectRels.map(r => ({
          source: r.source, target: r.target,
          note: r.note || r.explanation || 'Review needed'
        })),
        error: String(error)
      }))
      this.setOutputData(3, `${total} misconception(s) detected. Review the relationships between concepts.`)
    }
  }

  static register() {
    LiteGraph.registerNodeType(MisconceptionDetectorNode.path, MisconceptionDetectorNode)
  }
}
