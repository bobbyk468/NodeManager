/**
 * Smoke test: verifies that importing @haski/ta-lib auto-registers
 * all expected node types into LiteGraph.registered_node_types.
 *
 * The library calls LGraphRegisterCustomNodes() at module evaluation
 * time (nodes/index.ts line 45), so a plain import is sufficient.
 */
import { describe, expect, it } from 'vitest'

import { LiteGraph } from '@haski/ta-lib'

describe('node registration', () => {
  it('registers core input nodes', () => {
    expect(LiteGraph.registered_node_types['input/question']).toBeDefined()
    expect(LiteGraph.registered_node_types['input/answer']).toBeDefined()
    expect(LiteGraph.registered_node_types['input/sample-solution']).toBeDefined()
  })

  it('registers LLM node', () => {
    expect(LiteGraph.registered_node_types['models/llm']).toBeDefined()
  })

  it('registers output node', () => {
    expect(LiteGraph.registered_node_types['output/output']).toBeDefined()
  })

  it('registers ConceptGrade node', () => {
    expect(LiteGraph.registered_node_types['concept-aware/conceptgrade']).toBeDefined()
  })

  it('registers WeightedScore node', () => {
    expect(LiteGraph.registered_node_types['math/weighted_score']).toBeDefined()
  })

  it('registers utility nodes', () => {
    expect(LiteGraph.registered_node_types['utils/concat-string']).toBeDefined()
    expect(LiteGraph.registered_node_types['utils/concat-object']).toBeDefined()
    expect(LiteGraph.registered_node_types['basic/prompt-message']).toBeDefined()
  })
})
