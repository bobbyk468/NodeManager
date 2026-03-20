/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

/**
 * ConceptExtractorNode
 * 
 * Extracts domain concepts from student free-text answers using
 * LLM-based extraction (Groq API) with ontology-guided validation.
 * 
 * Part of the Concept-Aware Assessment Framework (Paper 1).
 * 
 * Inputs:
 *   - student_answer (string): The student's free-text response
 *   - question (string): The assessment question
 *   - domain_ontology (string): JSON string of domain ontology concepts
 * 
 * Outputs:
 *   - concept_graph (string): JSON student concept sub-graph
 *   - concepts_found (string): Comma-separated list of concepts found
 *   - num_concepts (string): Number of concepts extracted
 */
export class ConceptExtractorNode extends LGraphNode {
  env: Record<string, unknown>
  properties: {
    concept_graph: string
    concepts_found: string
    num_concepts: number
    confidence_threshold: number
  }

  constructor() {
    super()
    this.addIn('string', 'student answer')
    this.addIn('string', 'question')
    this.addIn('string', 'domain ontology (JSON)')
    this.addWidget(
      'slider',
      'confidence_threshold',
      0.3,
      (value: number) => {
        this.properties.confidence_threshold = value
      },
      { min: 0, max: 1, step: 0.05, precision: 2 }
    )
    this.addOut('string', 'concept graph (JSON)')
    this.addOut('string', 'concepts found')
    this.addOut('string', 'num concepts')
    this.properties = {
      concept_graph: '{}',
      concepts_found: '',
      num_concepts: 0,
      confidence_threshold: 0.3
    }
    this.title = 'Concept Extractor'
    this.serialize_widgets = true
    this.env = {}
  }

  static title = 'Concept Extractor'
  static path = 'concept-aware/concept-extractor'
  static getPath(): string {
    return ConceptExtractorNode.path
  }

  async init(_env: Record<string, unknown>) {
    this.env = _env
  }

  async onExecute() {
    if (typeof window !== 'undefined') {
      throw new Error('ConceptExtractorNode can only execute on the backend')
    }

    const studentAnswer = this.getInputData<string>(0) || ''
    const question = this.getInputData<string>(1) || ''
    const domainOntology = this.getInputData<string>(2) || '[]'

    if (!studentAnswer.trim()) {
      this.setOutputData(0, '{}')
      this.setOutputData(1, '')
      this.setOutputData(2, '0')
      return
    }

    // Build the LLM prompt for concept extraction
    const systemPrompt = `You are an expert Computer Science educator analyzing student answers about Data Structures and Algorithms.

Your task is to extract ALL domain concepts mentioned or implied in a student's response, and identify the relationships between them.

IMPORTANT RULES:
1. Extract concepts the student actually demonstrates understanding of
2. Identify relationships the student establishes between concepts
3. Use ONLY concepts from the provided domain ontology when possible
4. Capture misconceptions as incorrect relationships

Available relationship types: is_a, has_part, prerequisite_for, implements, uses, variant_of, has_property, has_complexity, operates_on, produces, contrasts_with`

    const userPrompt = `QUESTION: ${question}

STUDENT ANSWER: ${studentAnswer}

DOMAIN CONCEPTS: ${domainOntology}

Return ONLY valid JSON:
{
  "concepts_found": [
    {"id": "concept_id", "confidence": 0.0-1.0, "evidence": "quote", "is_correct_usage": true/false}
  ],
  "relationships_found": [
    {"source": "id", "target": "id", "relation_type": "type", "confidence": 0.0-1.0, "evidence": "quote", "is_correct": true/false, "misconception_note": ""}
  ],
  "overall_depth": "surface|moderate|deep"
}`

    const workerUrl = (this.env.MODEL_WORKER_URL as string) ?? 'https://api.groq.com/openai'
    const bearerToken = this.env.BEARER_TOKEN as string | undefined

    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (bearerToken) {
      headers['Authorization'] = `Bearer ${bearerToken}`
    }

    const requestBody = {
      model: 'llama-3.3-70b-versatile',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      temperature: 0.1,
      max_tokens: 2048
    }

    try {
      const response = await fetch(workerUrl + '/v1/chat/completions', {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`)
      }

      const data: any = await response.json()
      const content = data.choices?.[0]?.message?.content || '{}'

      // Parse the JSON response
      let parsed: any = {}
      try {
        // Handle markdown code blocks
        const jsonMatch = content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/)
        const jsonStr = jsonMatch ? jsonMatch[1] : content
        parsed = JSON.parse(jsonStr.trim())
      } catch {
        const start = content.indexOf('{')
        const end = content.lastIndexOf('}')
        if (start !== -1 && end !== -1) {
          parsed = JSON.parse(content.substring(start, end + 1))
        }
      }

      // Filter by confidence threshold
      const threshold = this.properties.confidence_threshold
      const filteredConcepts = (parsed.concepts_found || []).filter(
        (c: any) => (c.confidence || 0) >= threshold
      )

      const result = {
        question,
        student_answer: studentAnswer,
        concepts: filteredConcepts,
        relationships: parsed.relationships_found || [],
        overall_depth: parsed.overall_depth || 'surface',
        num_concepts: filteredConcepts.length
      }

      const conceptIds = filteredConcepts.map((c: any) => c.id).join(', ')

      this.properties.concept_graph = JSON.stringify(result)
      this.properties.concepts_found = conceptIds
      this.properties.num_concepts = filteredConcepts.length

      this.setOutputData(0, JSON.stringify(result))
      this.setOutputData(1, conceptIds)
      this.setOutputData(2, String(filteredConcepts.length))
    } catch (error) {
      console.error('ConceptExtractorNode error:', error)
      this.setOutputData(0, JSON.stringify({ error: String(error) }))
      this.setOutputData(1, '')
      this.setOutputData(2, '0')
    }
  }

  static register() {
    LiteGraph.registerNodeType(ConceptExtractorNode.path, ConceptExtractorNode)
  }
}
