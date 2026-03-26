import { LGraphRegisterCustomNodes } from '@haski/ta-lib'

/**
 * Register all custom LiteGraph nodes from @haski/ta-lib.
 * Delegates to LGraphRegisterCustomNodes which registers the full set:
 * AnswerInputNode, CleanNode, ConcatObject, ConcatString, CosineSimilarity,
 * CountNode, DocumentLoader, ExtractNumberNode, ImageNode, JSONParseNode,
 * KeywordCheckNode, LLMNode, MathOperationNode, MaxInputChars, MyAddNode,
 * NumberNode, OutputNode, Precision, PromptMessage, QuestionNode, Route,
 * SampleSolutionNode, SentenceTransformer, StringArrayToString, StringsToArray,
 * Textfield, TFIDF, Watch, WeightedScoreNode,
 * ConceptExtractorNode, KnowledgeGraphCompareNode, CognitiveDepthNode,
 * MisconceptionDetectorNode, ConceptGradeNode, NLQueryNode
 */
const registerNodes = () => {
  LGraphRegisterCustomNodes()
}

export default registerNodes
