/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */
import { LGraphNode, LiteGraph } from './litegraph-extensions'

/**
 * KnowledgeGraphCompareNode
 * 
 * Compares a student's concept sub-graph against an expert knowledge graph
 * to produce multi-dimensional assessment scores and diagnostic feedback.
 * 
 * Part of the Concept-Aware Assessment Framework (Paper 1).
 * 
 * Scoring dimensions:
 *   1. Concept Coverage — fraction of expected concepts the student mentioned
 *   2. Relationship Accuracy — are the relationships correct?
 *   3. Integration Quality — how well-connected is the student's knowledge?
 * 
 * Inputs:
 *   - student_graph (string): JSON from ConceptExtractorNode
 *   - expert_graph (string): JSON expert domain knowledge graph
 *   - expected_concepts (string): Comma-separated expected concept IDs
 * 
 * Outputs:
 *   - overall_score (string): Overall weighted score (0-1)
 *   - coverage_score (string): Concept coverage score (0-1)
 *   - accuracy_score (string): Relationship accuracy score (0-1)
 *   - integration_score (string): Integration quality score (0-1)
 *   - gap_report (string): JSON report of missing concepts and misconceptions
 *   - feedback (string): Human-readable diagnostic feedback
 */
export class KnowledgeGraphCompareNode extends LGraphNode {
  properties: {
    overall_score: number
    coverage_score: number
    accuracy_score: number
    integration_score: number
    coverage_weight: number
    accuracy_weight: number
    integration_weight: number
    depth_assessment: string
  }

  constructor() {
    super()
    this.addIn('string', 'student concept graph (JSON)')
    this.addIn('string', 'expert knowledge graph (JSON)')
    this.addIn('string', 'expected concepts (comma-separated)')
    
    // Scoring weight widgets
    this.addWidget(
      'slider', 'coverage_weight', 0.4,
      (v: number) => { this.properties.coverage_weight = v },
      { min: 0, max: 1, step: 0.05, precision: 2 }
    )
    this.addWidget(
      'slider', 'accuracy_weight', 0.3,
      (v: number) => { this.properties.accuracy_weight = v },
      { min: 0, max: 1, step: 0.05, precision: 2 }
    )
    this.addWidget(
      'slider', 'integration_weight', 0.3,
      (v: number) => { this.properties.integration_weight = v },
      { min: 0, max: 1, step: 0.05, precision: 2 }
    )

    this.addOut('string', 'overall score')
    this.addOut('string', 'coverage score')
    this.addOut('string', 'accuracy score')
    this.addOut('string', 'integration score')
    this.addOut('string', 'gap report (JSON)')
    this.addOut('string', 'feedback')

    this.properties = {
      overall_score: 0,
      coverage_score: 0,
      accuracy_score: 0,
      integration_score: 0,
      coverage_weight: 0.4,
      accuracy_weight: 0.3,
      integration_weight: 0.3,
      depth_assessment: 'surface'
    }
    this.title = 'KG Compare'
    this.serialize_widgets = true
  }

  static title = 'KG Compare'
  static path = 'concept-aware/kg-compare'
  static getPath(): string {
    return KnowledgeGraphCompareNode.path
  }

  async onExecute() {
    const studentGraphJson = this.getInputData<string>(0) || '{}'
    const expertGraphJson = this.getInputData<string>(1) || '{}'
    const expectedConceptsStr = this.getInputData<string>(2) || ''

    let studentGraph: any = {}
    let expertGraph: any = {}

    try {
      studentGraph = JSON.parse(studentGraphJson)
      expertGraph = JSON.parse(expertGraphJson)
    } catch {
      this.setOutputData(0, '0')
      this.setOutputData(5, 'Error: Invalid JSON input')
      return
    }

    const expectedConcepts = expectedConceptsStr
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)

    // Build expert concept lookup
    const expertConcepts: Record<string, any> = {}
    for (const c of (expertGraph.concepts || [])) {
      expertConcepts[c.id] = c
    }

    // Build expert edge lookup
    const expertEdges: Set<string> = new Set()
    for (const r of (expertGraph.relationships || [])) {
      expertEdges.add(`${r.source_id}|${r.target_id}|${r.relation_type}`)
      // Also add reverse for symmetric relations
      if (r.relation_type === 'contrasts_with') {
        expertEdges.add(`${r.target_id}|${r.source_id}|${r.relation_type}`)
      }
    }

    // Student concepts
    const studentConcepts = (studentGraph.concepts || [])
      .map((c: any) => c.id || c.concept_id)
      .filter(Boolean)
    const studentConceptSet = new Set(studentConcepts)
    const studentRelationships = studentGraph.relationships || []

    // === 1. Concept Coverage ===
    const targetConcepts = expectedConcepts.length > 0 ? expectedConcepts : studentConcepts
    let matchedConcepts: string[] = []
    let missingConcepts: string[] = []

    if (targetConcepts.length > 0) {
      for (const cid of targetConcepts) {
        if (studentConceptSet.has(cid)) {
          matchedConcepts.push(cid)
        } else {
          missingConcepts.push(cid)
        }
      }
    }

    const coverageScore = targetConcepts.length > 0
      ? matchedConcepts.length / targetConcepts.length
      : 0

    // === 2. Relationship Accuracy ===
    let correctRels = 0
    let incorrectRels = 0
    const misconceptions: any[] = []

    for (const rel of studentRelationships) {
      const source = rel.source || rel.source_id
      const target = rel.target || rel.target_id
      const relType = rel.relation_type

      if (rel.is_correct === false) {
        incorrectRels++
        misconceptions.push({
          source, target,
          student_relation: relType,
          note: rel.misconception_note || 'Incorrect relationship'
        })
        continue
      }

      // Check against expert graph
      const edgeKey = `${source}|${target}|${relType}`
      const reverseKey = `${target}|${source}|${relType}`
      if (expertEdges.has(edgeKey) || expertEdges.has(reverseKey)) {
        correctRels++
      } else {
        // Check if any relationship exists between these concepts
        let hasAnyRel = false
        for (const r of (expertGraph.relationships || [])) {
          if ((r.source_id === source && r.target_id === target) ||
              (r.source_id === target && r.target_id === source)) {
            hasAnyRel = true
            misconceptions.push({
              source, target,
              student_relation: relType,
              correct_relation: r.relation_type,
              note: `Wrong relation type: used '${relType}' but should be '${r.relation_type}'`
            })
            incorrectRels++
            break
          }
        }
        if (!hasAnyRel) {
          // Relationship not found in expert graph — treat as hallucination/incorrect
          incorrectRels++
          misconceptions.push({
            source, target,
            student_relation: relType,
            correct_relation: null,
            note: `Relationship '${relType}' between '${source}' and '${target}' is not present in the expert knowledge graph`
          })
        }
      }
    }

    const totalRels = correctRels + incorrectRels
    const accuracyScore = totalRels > 0 ? correctRels / totalRels : 1.0

    // === 3. Integration Quality ===
    // Matches the Python comparator._compute_integration_quality formula exactly.

    // 3a. Relationship coverage: how many expert edges between student concepts
    //     does the student actually demonstrate?
    let expectedRelCount = 0
    let foundRelCount = 0

    for (const r of (expertGraph.relationships || [])) {
      if (studentConceptSet.has(r.source_id) && studentConceptSet.has(r.target_id)) {
        expectedRelCount++
        const hasStudentRel = studentRelationships.some((sr: any) => {
          const s = sr.source || sr.source_id
          const t = sr.target || sr.target_id
          return (s === r.source_id && t === r.target_id) ||
                 (s === r.target_id && t === r.source_id)
        })
        if (hasStudentRel) foundRelCount++
      }
    }

    // Avoid double-counting (each undirected edge counted from both directions)
    expectedRelCount = Math.max(Math.ceil(expectedRelCount / 2), 1)
    foundRelCount = Math.ceil(foundRelCount / 2)

    // 3b. Graph density (matches Python: connectivity = edges / max_possible_edges)
    const n = studentConcepts.length
    const maxPossibleEdges = n * (n - 1) / 2
    const connectivity = maxPossibleEdges > 0
      ? studentRelationships.length / maxPossibleEdges
      : 0

    // 3c. Isolation penalty
    const connectedConcepts = new Set<string>()
    for (const rel of studentRelationships) {
      connectedConcepts.add(rel.source || rel.source_id)
      connectedConcepts.add(rel.target || rel.target_id)
    }
    const isolatedCount = studentConcepts.filter((c: string) => !connectedConcepts.has(c)).length
    const isolationPenalty = n > 0 ? isolatedCount / n : 0

    const relCoverage = foundRelCount / expectedRelCount

    // Weights: 0.3 density + 0.3 (1-isolation) + 0.4 rel_coverage — mirrors Python
    const integrationScore = Math.min(
      0.3 * Math.min(connectivity * 3, 1.0) +
      0.3 * (1.0 - isolationPenalty) +
      0.4 * relCoverage,
      1.0
    )

    // === Overall Score ===
    const w = this.properties
    const overallScore = (
      w.coverage_weight * coverageScore +
      w.accuracy_weight * accuracyScore +
      w.integration_weight * integrationScore
    )

    // === Depth Assessment ===
    let depthAssessment = 'surface'
    if (coverageScore > 0.7 && accuracyScore > 0.8 && integrationScore > 0.6) {
      depthAssessment = 'deep'
    } else if (coverageScore > 0.4 && studentRelationships.length >= 2) {
      depthAssessment = 'moderate'
    }

    // === Gap Report ===
    const gapReport = {
      matched_concepts: matchedConcepts,
      missing_concepts: missingConcepts.map(id => ({
        id,
        name: expertConcepts[id]?.name || id
      })),
      misconceptions,
      depth: depthAssessment
    }

    // === Feedback ===
    const feedbackLines: string[] = []
    if (coverageScore > 0.7) feedbackLines.push('Good concept coverage.')
    if (accuracyScore > 0.8) feedbackLines.push('Accurate understanding of relationships.')
    if (integrationScore > 0.6) feedbackLines.push('Well-connected knowledge.')
    
    if (missingConcepts.length > 0) {
      const names = missingConcepts
        .map(id => expertConcepts[id]?.name || id)
        .join(', ')
      feedbackLines.push(`Missing concepts: ${names}`)
    }
    if (misconceptions.length > 0) {
      feedbackLines.push(`${misconceptions.length} misconception(s) detected.`)
    }
    if (depthAssessment === 'surface') {
      feedbackLines.push('Try explaining how concepts relate, not just listing them.')
    }

    const feedback = feedbackLines.join(' ')

    // Set outputs
    this.properties.overall_score = overallScore
    this.properties.coverage_score = coverageScore
    this.properties.accuracy_score = accuracyScore
    this.properties.integration_score = integrationScore
    this.properties.depth_assessment = depthAssessment

    this.setOutputData(0, overallScore.toFixed(4))
    this.setOutputData(1, coverageScore.toFixed(4))
    this.setOutputData(2, accuracyScore.toFixed(4))
    this.setOutputData(3, integrationScore.toFixed(4))
    this.setOutputData(4, JSON.stringify(gapReport))
    this.setOutputData(5, feedback)
  }

  static register() {
    LiteGraph.registerNodeType(KnowledgeGraphCompareNode.path, KnowledgeGraphCompareNode)
  }
}
