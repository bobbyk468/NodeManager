/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

// ── CS Data Structures Misconception Taxonomy ──────────────────────────────
// Mirrors detector.py CS_MISCONCEPTION_TAXONOMY for consistent taxonomy-matched
// misconception IDs (DS-LINK-01 etc.) between the Python and TS implementations.
const CS_MISCONCEPTION_TAXONOMY: Record<string, {
  category: string; description: string; concepts: string[]
  common_claim: string; correct: string; severity: string
}> = {
  'DS-LINK-01': {
    category: 'Linked Lists',
    description: 'Confusing array indices with pointer-based access',
    concepts: ['linked_list', 'array', 'pointer', 'index'],
    common_claim: 'You can access linked list elements by index in O(1)',
    correct: 'Linked list access requires O(n) traversal; only arrays support O(1) index access',
    severity: 'critical',
  },
  'DS-LINK-02': {
    category: 'Linked Lists',
    description: 'Believing linked lists use contiguous memory',
    concepts: ['linked_list', 'array', 'static_memory', 'dynamic_memory'],
    common_claim: 'Linked list nodes are stored next to each other in memory',
    correct: 'Linked list nodes are dynamically allocated and can be anywhere in memory',
    severity: 'critical',
  },
  'DS-LINK-03': {
    category: 'Linked Lists',
    description: 'Thinking insertion is always O(1) in linked lists',
    concepts: ['linked_list', 'insertion', 'o_1', 'o_n'],
    common_claim: 'Insertion in a linked list is always O(1)',
    correct: 'Insertion at HEAD is O(1), but insertion at a specific position requires O(n) traversal first',
    severity: 'moderate',
  },
  'DS-STACK-01': {
    category: 'Stacks & Queues',
    description: 'Confusing LIFO (stack) with FIFO (queue)',
    concepts: ['stack', 'queue', 'lifo', 'fifo'],
    common_claim: 'A stack follows First In First Out order',
    correct: 'A stack follows LIFO; a queue follows FIFO',
    severity: 'critical',
  },
  'DS-STACK-02': {
    category: 'Stacks & Queues',
    description: 'Thinking stacks can only be implemented with arrays',
    concepts: ['stack', 'array', 'linked_list'],
    common_claim: 'Stacks must use arrays as the underlying storage',
    correct: 'Stacks can be implemented with either arrays or linked lists',
    severity: 'minor',
  },
  'DS-TREE-01': {
    category: 'Trees',
    description: 'Assuming all binary trees are binary search trees',
    concepts: ['binary_tree', 'binary_search_tree'],
    common_claim: 'Any binary tree has the ordered property (left < root < right)',
    correct: 'Only BSTs maintain the ordering property; a general binary tree has no ordering constraint',
    severity: 'critical',
  },
  'DS-TREE-02': {
    category: 'Trees',
    description: 'Confusing tree height with number of nodes',
    concepts: ['tree', 'tree_height', 'node'],
    common_claim: 'A tree with n nodes has height n',
    correct: 'Tree height is the longest root-to-leaf path; a balanced tree has height O(log n)',
    severity: 'moderate',
  },
  'DS-TREE-03': {
    category: 'Trees',
    description: 'Thinking BST operations are always O(log n)',
    concepts: ['binary_search_tree', 'o_log_n', 'balanced_tree'],
    common_claim: 'BST search/insert is always O(log n)',
    correct: 'BST operations are O(log n) only when balanced; worst case is O(n)',
    severity: 'moderate',
  },
  'DS-HASH-01': {
    category: 'Hash Tables',
    description: 'Assuming hash tables never have worst-case O(n)',
    concepts: ['hash_table', 'collision', 'o_1', 'o_n'],
    common_claim: 'Hash table operations are always O(1)',
    correct: 'Hash table operations are O(1) average; worst case with many collisions is O(n)',
    severity: 'moderate',
  },
  'DS-HASH-02': {
    category: 'Hash Tables',
    description: 'Confusing hash function with encryption',
    concepts: ['hash_function', 'hash_table'],
    common_claim: 'Hash functions encrypt the data for security',
    correct: 'Hash functions in hash tables map keys to indices; not for security',
    severity: 'minor',
  },
  'DS-SORT-01': {
    category: 'Sorting',
    description: 'Believing quicksort is always faster than merge sort',
    concepts: ['quick_sort', 'merge_sort', 'o_n_log_n', 'o_n2'],
    common_claim: 'Quick sort is always the fastest sorting algorithm',
    correct: 'Quick sort average is O(n log n) but worst case is O(n²); merge sort guarantees O(n log n)',
    severity: 'moderate',
  },
  'DS-SORT-02': {
    category: 'Sorting',
    description: 'Thinking all O(n log n) sorts are equally fast in practice',
    concepts: ['merge_sort', 'quick_sort', 'heap_sort'],
    common_claim: 'Merge sort and quick sort have the same performance',
    correct: 'Quick sort is often faster due to better cache locality despite same asymptotic complexity',
    severity: 'minor',
  },
  'DS-GRAPH-01': {
    category: 'Graphs',
    description: 'Assuming BFS always finds the shortest path',
    concepts: ['bfs', 'shortest_path', 'weighted_graph', 'dijkstra'],
    common_claim: 'BFS finds the shortest path in any graph',
    correct: 'BFS finds shortest paths in UNWEIGHTED graphs only; use Dijkstra for weighted graphs',
    severity: 'moderate',
  },
  'DS-GRAPH-02': {
    category: 'Graphs',
    description: 'Confusing DFS with BFS behavior',
    concepts: ['bfs', 'dfs', 'queue', 'stack'],
    common_claim: 'DFS uses a queue / BFS uses a stack',
    correct: 'BFS uses a queue (level-by-level); DFS uses a stack (depth-first)',
    severity: 'critical',
  },
  'DS-COMP-01': {
    category: 'Complexity',
    description: 'Confusing best case with average case complexity',
    concepts: ['time_complexity', 'big_o_notation'],
    common_claim: 'Big-O notation describes the best case',
    correct: 'Big-O describes the UPPER BOUND (worst case)',
    severity: 'moderate',
  },
  'DS-COMP-02': {
    category: 'Complexity',
    description: 'Thinking O(n²) is always slower than O(n log n)',
    concepts: ['o_n2', 'o_n_log_n', 'time_complexity'],
    common_claim: 'O(n log n) algorithms are always faster than O(n²)',
    correct: 'For small n, O(n²) algorithms with low constant factors can be faster',
    severity: 'minor',
  },
}

/** Find taxonomy matches for a set of student concepts (≥1 overlap, sorted by overlap size). */
function findTaxonomyMatches(studentConcepts: Set<string>): Array<[string, typeof CS_MISCONCEPTION_TAXONOMY[string], number]> {
  const matches: Array<[string, typeof CS_MISCONCEPTION_TAXONOMY[string], number]> = []
  for (const [taxId, tax] of Object.entries(CS_MISCONCEPTION_TAXONOMY)) {
    const overlap = tax.concepts.filter(c => studentConcepts.has(c)).length
    if (overlap >= 1) matches.push([taxId, tax, overlap])
  }
  return matches.sort((a, b) => b[2] - a[2])
}

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

    // Taxonomy matching — mirrors Python detector._find_taxonomy_matches
    const taxonomyMatches = findTaxonomyMatches(studentConcepts)
    const taxonomyStr = taxonomyMatches.map(([taxId, tax]) =>
      `- ${taxId}: ${tax.description} (severity: ${tax.severity})\n` +
      `  Common claim: "${tax.common_claim}"\n` +
      `  Correct: "${tax.correct}"`
    ).join('\n') || 'No direct taxonomy matches found.'

    // Build misconception analysis prompt
    const incorrectStr = incorrectRels.map((r: any) =>
      `- ${r.source || '?'} → ${r.target || '?'} (used: '${r.student_relation || '?'}'` +
      `${r.correct_relation ? `, correct: '${r.correct_relation}'` : ''}` +
      `)\n  Note: ${r.note || r.explanation || 'N/A'}`
    ).join('\n')

    const systemPrompt = `You are an expert CS educator analyzing student misconceptions about Data Structures and Algorithms.
For each incorrect relationship, determine:
1. Type: systematic (deep misunderstanding), isolated (one-off), knowledge_gap, conflation, overgeneralization, or undergeneralization
2. Severity: critical (blocks learning), moderate (causes problems), minor (imprecise)
3. Match to the provided taxonomy entry if applicable (use its ID as taxonomy_match)
4. Provide a clear explanation and remediation hint for the student.`

    const userPrompt = `QUESTION: ${question}
STUDENT ANSWER: ${studentAnswer}
INCORRECT RELATIONSHIPS:
${incorrectStr}

KNOWN MISCONCEPTION TAXONOMY MATCHES:
${taxonomyStr}

Return ONLY valid JSON:
{
  "misconceptions": [
    {
      "taxonomy_match": "DS-XXX-NN or 'novel'",
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
      for (const m of misconceptions) {
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
