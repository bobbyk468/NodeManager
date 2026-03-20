/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

/**
 * NLQueryNode (V-NLI Node)
 *
 * Natural Language Query interface for educational analytics.
 * Accepts educator questions in plain English and returns
 * structured query results with visualization specifications.
 *
 * Part of the Concept-Aware Assessment Framework (Paper 3).
 *
 * Inputs:
 *   - query (string): Natural language educator query
 *   - assessment_data (string): JSON array of student assessments
 *
 * Outputs:
 *   - query_type (string): Classified query type
 *   - visualization_type (string): Recommended visualization
 *   - result_data (string): JSON with query results
 *   - insights (string): Auto-generated text insights
 */
export class NLQueryNode extends LGraphNode {
  env: Record<string, unknown>
  properties: {
    query_type: string
    visualization_type: string
  }

  constructor() {
    super()
    this.addIn('string', 'educator query')
    this.addIn('string', 'assessment data (JSON)')
    this.addOut('string', 'query type')
    this.addOut('string', 'visualization type')
    this.addOut('string', 'result data (JSON)')
    this.addOut('string', 'insights')
    this.properties = {
      query_type: '',
      visualization_type: ''
    }
    this.title = 'V-NLI Query'
    this.serialize_widgets = true
    this.env = {}
  }

  static title = 'V-NLI Query'
  static path = 'concept-aware/nl-query'
  static getPath(): string {
    return NLQueryNode.path
  }

  async init(_env: Record<string, unknown>) {
    this.env = _env
  }

  async onExecute() {
    if (typeof window !== 'undefined') {
      throw new Error('NLQueryNode can only execute on the backend')
    }

    const query = this.getInputData<string>(0) || ''
    const assessmentDataJson = this.getInputData<string>(1) || '[]'

    if (!query.trim()) {
      this.setOutputData(0, '')
      this.setOutputData(1, '')
      this.setOutputData(2, '{}')
      this.setOutputData(3, 'No query provided.')
      return
    }

    let assessments: any[] = []
    try {
      assessments = JSON.parse(assessmentDataJson)
    } catch { /* use empty */ }

    const workerUrl = (this.env.MODEL_WORKER_URL as string) ?? 'https://api.groq.com/openai'
    const bearerToken = this.env.BEARER_TOKEN as string | undefined
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (bearerToken) headers['Authorization'] = `Bearer ${bearerToken}`

    try {
      // Parse the natural language query
      const parsePrompt = `You are a query parser for an educational analytics system.

Parse this educator query into a structured operation:
"${query}"

Assessment data contains ${assessments.length} student records with:
- blooms (level, label), solo (level, label)
- concept_graph (concepts, relationships)
- misconceptions (list with severity)
- overall_score, depth_category

Return ONLY valid JSON:
{
  "query_type": "bloom_distribution|solo_distribution|misconception_analysis|concept_analysis|student_comparison|class_summary",
  "visualization_type": "bar_chart|heatmap|radar|table",
  "description": "what the educator wants to know",
  "insights": ["insight 1", "insight 2"]
}`

      const response = await fetch(workerUrl + '/v1/chat/completions', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          model: 'llama-3.3-70b-versatile',
          messages: [
            { role: 'system', content: 'Parse educational analytics queries.' },
            { role: 'user', content: parsePrompt }
          ],
          temperature: 0.1,
          max_tokens: 1000
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

      const queryType = parsed.query_type || 'class_summary'
      const vizType = parsed.visualization_type || 'table'
      const description = parsed.description || ''
      const insights = (parsed.insights || []).join('\n')

      // Execute query against assessment data
      const resultData = this.executeQuery(queryType, assessments)

      this.properties.query_type = queryType
      this.properties.visualization_type = vizType

      this.setOutputData(0, queryType)
      this.setOutputData(1, vizType)
      this.setOutputData(2, JSON.stringify(resultData))
      this.setOutputData(3, `${description}\n\n${insights}`)

    } catch (error) {
      console.error('NLQueryNode error:', error)
      this.setOutputData(0, 'error')
      this.setOutputData(1, 'table')
      this.setOutputData(2, JSON.stringify({ error: String(error) }))
      this.setOutputData(3, 'Query processing failed.')
    }
  }

  private executeQuery(queryType: string, assessments: any[]): any {
    switch (queryType) {
      case 'bloom_distribution': {
        const dist: Record<string, number> = {}
        for (const a of assessments) {
          const label = a.blooms?.label || 'Unknown'
          dist[label] = (dist[label] || 0) + 1
        }
        return { distribution: dist, total: assessments.length }
      }
      case 'solo_distribution': {
        const dist: Record<string, number> = {}
        for (const a of assessments) {
          const label = a.solo?.label || 'Unknown'
          dist[label] = (dist[label] || 0) + 1
        }
        return { distribution: dist, total: assessments.length }
      }
      case 'misconception_analysis': {
        const allMisc: any[] = []
        for (const a of assessments) {
          for (const m of (a.misconceptions?.misconceptions || [])) {
            allMisc.push({ ...m, student_id: a.student_id })
          }
        }
        return { total: allMisc.length, misconceptions: allMisc.slice(0, 20) }
      }
      case 'student_comparison': {
        return {
          students: assessments.map(a => ({
            id: a.student_id,
            blooms: a.blooms?.label,
            solo: a.solo?.label,
            score: a.overall_score,
            misconceptions: a.misconceptions?.total_misconceptions || 0
          }))
        }
      }
      default: {
        const avgScore = assessments.length > 0
          ? assessments.reduce((s, a) => s + (a.overall_score || 0), 0) / assessments.length
          : 0
        return {
          num_students: assessments.length,
          average_score: avgScore.toFixed(3),
          summary: `${assessments.length} students assessed`
        }
      }
    }
  }

  static register() {
    LiteGraph.registerNodeType(NLQueryNode.path, NLQueryNode)
  }
}
