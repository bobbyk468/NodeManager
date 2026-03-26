import { LGraphNode, LiteGraph } from 'litegraph.js'

export class JSONParseNode extends LGraphNode {
  constructor() {
    super()
    this.addInput('json_string', 'string')
    this.addInput('key', 'string')
    
    this.addOutput('value', 'string,number,boolean,object,array')
    this.addOutput('error', 'boolean')
    
    this.properties = {
      key: 'score'
    }
    this.addWidget('text', 'Key to extract', this.properties.key, (v: string) => {
      this.properties.key = v
    })
    
    this.title = 'JSON Parse'
    this.properties.desc = 'Parses a JSON string and extracts a specific key'
  }

  onExecute() {
    const jsonStr = this.getInputData(0)
    let key = this.getInputData(1)
    
    if (!key) {
      key = this.properties.key
    }
    
    if (!jsonStr) {
      this.setOutputData(0, null)
      this.setOutputData(1, true)
      return
    }
    
    try {
      const parsed = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr
      
      if (key && parsed !== null && typeof parsed === 'object') {
        const val = parsed[key]
        this.setOutputData(0, val !== undefined ? val : null)
      } else {
        this.setOutputData(0, parsed)
      }
      this.setOutputData(1, false)
    } catch (e) {
      console.error('Failed to parse JSON in JSONParseNode:', e)
      this.setOutputData(0, null)
      this.setOutputData(1, true)
    }
  }
}

LiteGraph.registerNodeType('basic/json_parse', JSONParseNode)
