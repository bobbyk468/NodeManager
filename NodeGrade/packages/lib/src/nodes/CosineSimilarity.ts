/* eslint-disable immutable/no-let */
/* eslint-disable immutable/no-mutation */
/* eslint-disable immutable/no-this */

import { LGraphNode, LiteGraph } from './litegraph-extensions'

/**
 * Cosine Similarity — accepts either pre-computed embedding vectors ([number])
 * or raw strings. When strings are received the node calls the sentence-
 * embedding worker to obtain vectors before computing cosine similarity.
 */
export class CosineSimilarity extends LGraphNode {
  env: Record<string, unknown>

  constructor() {
    super()

    // Accept any type so both strings and number arrays work
    this.addIn('*')
    this.addIn('*')

    this.addOut('number')
    this.properties = {
      value: -1
    }
    this.title = 'Cosine Similarity'
    this.env = {}
  }

  //name of the node
  static title = 'Cosine Similarity'
  static path = 'models/cosine-similarity'

  static getPath(): string {
    return CosineSimilarity.path
  }

  async init(_env: Record<string, unknown>) {
    this.env = _env
  }

  // Calculates cosine similarity between two arrays of numbers
  cosineSimilarity(a: number[], b: number[]): number {
    let dotProduct = 0
    let normA = 0
    let normB = 0
    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i]
      normA += a[i] * a[i]
      normB += b[i] * b[i]
    }
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB))
  }

  /**
   * Convert a string to an embedding vector via the sentence-embedding worker.
   */
  private async toEmbedding(input: unknown): Promise<number[]> {
    if (Array.isArray(input) && typeof input[0] === 'number') {
      // Already an embedding vector
      return input as number[]
    }

    // Must be a string — call the similarity worker
    const url =
      ((this.env?.SIMILARITY_WORKER_URL as string) ?? 'http://localhost:8002') +
      '/sentence_embedding'

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sentence: String(input) })
    })

    if (!response.ok) {
      throw new Error(
        `Sentence embedding request failed: ${response.status} ${response.statusText}`
      )
    }

    return (await response.json()) as number[]
  }

  //name of the function to call when executing
  async onExecute() {
    const input_one = this.getInputData(0)
    const input_two = this.getInputData(1)
    if (input_one && input_two) {
      const [emb_one, emb_two] = await Promise.all([
        this.toEmbedding(input_one),
        this.toEmbedding(input_two)
      ])
      const similarity = this.cosineSimilarity(emb_one, emb_two)
      this.setOutputData(0, similarity)
    }
  }

  //register in the system
  static register() {
    LiteGraph.registerNodeType(CosineSimilarity.path, CosineSimilarity)
  }
}
