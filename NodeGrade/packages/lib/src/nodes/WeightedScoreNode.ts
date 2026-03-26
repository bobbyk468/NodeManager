import { LGraphNode, LiteGraph } from 'litegraph.js'

export class WeightedScoreNode extends LGraphNode {
  constructor() {
    super()
    
    // Inputs for the scores to combine
    this.addInput('score_1', 'number')
    this.addInput('score_2', 'number')
    
    // Output the final combined score
    this.addOutput('final_score', 'number')
    
    // Properties for the weights
    this.properties = {
      weight_1: 0.5,
      weight_2: 0.5,
      normalize_to_100: false // Option to normalize inputs that might be 0-1 (like cosine similarity) to 0-100
    }
    
    // Widgets to adjust weights in the UI
    this.addWidget('number', 'Weight 1', this.properties.weight_1, (v: number) => {
      this.properties.weight_1 = v
    }, { min: 0, max: 1, step: 0.05 })
    
    this.addWidget('number', 'Weight 2', this.properties.weight_2, (v: number) => {
      this.properties.weight_2 = v
    }, { min: 0, max: 1, step: 0.05 })
    
    this.addWidget('toggle', 'Normalize 0-1 to 0-100', this.properties.normalize_to_100, (v: boolean) => {
      this.properties.normalize_to_100 = v
    })
    
    this.title = 'Weighted Score'
    this.properties.desc = 'Combines multiple scores using configurable weights'
  }

  onExecute() {
    let s1 = this.getInputData(0)
    let s2 = this.getInputData(1)
    
    // Default to 0 if inputs are missing or invalid
    if (typeof s1 !== 'number') s1 = parseFloat(s1) || 0
    if (typeof s2 !== 'number') s2 = parseFloat(s2) || 0
    
    // Optional normalization (e.g. if Cosine Similarity outputs 0.85 and LLM outputs 85)
    if (this.properties.normalize_to_100) {
      if (s1 <= 1 && s1 >= -1) s1 = s1 * 100
      if (s2 <= 1 && s2 >= -1) s2 = s2 * 100
    }
    
    const w1 = Number(this.properties.weight_1) || 0
    const w2 = Number(this.properties.weight_2) || 0
    
    // Calculate weighted sum
    // If weights don't sum to 1, we normalize them during calculation
    const totalWeight = w1 + w2
    
    let finalScore = 0
    if (totalWeight > 0) {
      finalScore = ((s1 * w1) + (s2 * w2)) / totalWeight
    }
    
    // Round to 2 decimal places for cleaner output
    finalScore = Math.round(finalScore * 100) / 100
    
    this.setOutputData(0, finalScore)
  }
}

LiteGraph.registerNodeType('math/weighted_score', WeightedScoreNode)
