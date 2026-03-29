import { test, expect } from '@playwright/test'

test.describe('Suite 5 — Starter Templates', () => {
  test('5.1 starter.json — 4 nodes', async ({ request }) => {
    const res = await request.get('http://localhost:5173/templates/starter.json')
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(Array.isArray(body.nodes)).toBe(true)
    expect(body.nodes.length).toBe(4)
  })

  test('5.2 concept-grade.json — 7 nodes, domain node wired to slot 2', async ({ request }) => {
    const res = await request.get('http://localhost:5173/templates/concept-grade.json')
    expect(res.status()).toBe(200)
    const body = await res.json()
    // 7 nodes: question, answer, domain, conceptgrade, score-out, depth-out, feedback-out
    expect(body.nodes.length).toBe(7)
    expect(body.links.length).toBeGreaterThan(0)
    // Domain input node exists
    const domainNode = body.nodes.find((n: { type: string }) => n.type === 'input/text')
    expect(domainNode).toBeDefined()
    expect(domainNode.title).toBe('Subject Domain')
    // ConceptGradeNode has domain wired to slot 2
    const cg = body.nodes.find((n: { type: string }) => n.type === 'concept-aware/conceptgrade')
    expect(cg).toBeDefined()
    const domainInput = cg.inputs.find((inp: { name: string }) => inp.name === 'domain')
    expect(domainInput).toBeDefined()
    expect(domainInput.slot_index).toBe(2)
  })

  test('5.3 llm-grader.json — ≥10 nodes, links present', async ({ request }) => {
    const res = await request.get('http://localhost:5173/templates/llm-grader.json')
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(body.nodes.length).toBeGreaterThanOrEqual(10)
    expect(body.links.length).toBeGreaterThan(0)
  })
})
