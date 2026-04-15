/**
 * conceptAliases.ts — Semantic alias matching for rubric-edit causal attribution.
 *
 * Solves the lexical mismatch problem identified in Gemini's v3 review:
 * an educator may type "step size" when the LRM trace flagged "learning_rate".
 * Strict string equality would register a false negative for concept_in_contradicts.
 *
 * Strategy (three layers, applied in order):
 *   1. Normalise both strings (lowercase, underscore→space, trim whitespace)
 *   2. Check DOMAIN_ALIASES dictionary (curated domain-specific synonyms)
 *   3. Compute Levenshtein similarity ratio — flag as match if ratio ≥ FUZZY_THRESHOLD
 *
 * Usage:
 *   const result = matchesContradictsNode('step size', ['learning_rate', 'dropout']);
 *   // → { matched: true, bestMatch: 'learning_rate', score: 1.0 }  (via alias dict)
 */

// ── Configuration ─────────────────────────────────────────────────────────────

/** Levenshtein similarity ratio required to count as a semantic match. */
const FUZZY_THRESHOLD = 0.80;

// ── Domain alias dictionary ───────────────────────────────────────────────────
//
// Keys are canonical concept IDs (underscored, matching KG node IDs).
// Values are arrays of accepted synonyms (any casing; the normaliser lowercases them).
//
// Covers Neural Network (DigiKlausur) and CS Data Structures (Mohler) domains.

const DOMAIN_ALIASES: Record<string, string[]> = {
  // ── Neural network / ML ────────────────────────────────────────────────────
  learning_rate: [
    'step size', 'step_size', 'lr', 'alpha', 'learning rate',
    'stepsize', 'update rate', 'step length',
  ],
  gradient_descent: [
    'gd', 'sgd', 'stochastic gradient descent', 'batch gradient descent',
    'gradient update', 'gradient step', 'gradient optimisation', 'gradient optimization',
  ],
  backpropagation: [
    'backprop', 'back propagation', 'backward pass', 'backward propagation',
    'back prop', 'error backpropagation', 'chain rule gradient',
  ],
  activation_function: [
    'activation', 'nonlinearity', 'transfer function', 'activation fn',
    'non-linearity',
  ],
  neural_network: [
    'nn', 'artificial neural network', 'ann', 'deep network', 'mlp',
    'multilayer perceptron', 'multi layer perceptron',
  ],
  loss_function: [
    'cost function', 'objective function', 'error function', 'loss',
    'training loss', 'criterion',
  ],
  overfitting: [
    'over-fitting', 'overfit', 'high variance', 'model overfit',
  ],
  underfitting: [
    'under-fitting', 'underfit', 'high bias', 'model underfit',
  ],
  regularization: [
    'regularisation', 'l1 regularisation', 'l2 regularisation',
    'weight decay', 'dropout regularisation', 'l1', 'l2',
  ],
  dropout: [
    'dropout layer', 'drop out', 'dropout regularization',
  ],
  batch_size: [
    'mini-batch', 'mini batch', 'batch', 'minibatch size',
  ],
  epoch: [
    'training epoch', 'iteration', 'pass', 'training iteration',
  ],
  weight: [
    'parameter', 'model weight', 'synaptic weight', 'network weight',
  ],
  bias: [
    'bias term', 'intercept', 'bias unit', 'offset',
  ],
  softmax: [
    'softmax function', 'normalized exponential', 'softmax activation',
  ],
  relu: [
    'rectified linear unit', 'rectified linear', 'rlu', 'relu activation',
  ],
  sigmoid: [
    'logistic function', 'logistic sigmoid', 'sigmoid activation',
  ],
  convolution: [
    'conv', 'convolutional layer', 'conv layer', 'feature map',
  ],
  pooling: [
    'max pooling', 'average pooling', 'pool', 'pooling layer',
    'avg pooling', 'maxpool',
  ],
  batch_normalisation: [
    'batch normalization', 'batch norm', 'batchnorm', 'normalisation layer',
    'normalization layer',
  ],
  vanishing_gradient: [
    'vanishing gradients', 'gradient vanishing', 'dying gradient',
  ],
  // ── CS Data Structures (Mohler) ────────────────────────────────────────────
  linked_list: [
    'linked list', 'singly linked list', 'doubly linked list', 'sll', 'dll',
  ],
  binary_tree: [
    'binary tree', 'bst', 'binary search tree', 'btree',
  ],
  recursion: [
    'recursive', 'recursive function', 'self-referential', 'recursive call',
  ],
  pointer: [
    'reference', 'memory address', 'memory pointer', 'ptr',
  ],
  stack: [
    'call stack', 'lifo', 'last in first out', 'stack data structure',
  ],
  queue: [
    'fifo', 'first in first out', 'queue data structure',
  ],
  hash_table: [
    'hash map', 'hashmap', 'dictionary', 'associative array', 'hash',
  ],
  sorting: [
    'sort', 'sort algorithm', 'sorting algorithm', 'sort function',
  ],
  time_complexity: [
    'big o', 'big-o', 'o notation', 'asymptotic complexity',
    'computational complexity', 'runtime complexity', 'time complexity analysis',
  ],
};

// ── Normalisation ─────────────────────────────────────────────────────────────

/** Lowercase, replace underscores with spaces, collapse whitespace, trim. */
export function normalizeConceptId(id: string): string {
  return id.toLowerCase().replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
}

// ── Levenshtein distance ──────────────────────────────────────────────────────

function levenshteinDistance(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  // dp[i][j] = edit distance between a[0..i-1] and b[0..j-1]
  const dp: number[][] = Array.from({ length: m + 1 }, (_, i) =>
    Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)),
  );
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[m][n];
}

/** Similarity ratio in [0, 1]. 1.0 = identical. */
function similarityRatio(a: string, b: string): number {
  if (a === b) return 1.0;
  const maxLen = Math.max(a.length, b.length);
  if (maxLen === 0) return 1.0;
  return 1 - levenshteinDistance(a, b) / maxLen;
}

// ── Main API ──────────────────────────────────────────────────────────────────

export interface ConceptMatchResult {
  matched: boolean;
  bestMatch: string | null;   // canonical CONTRADICTS nodeId that matched
  score: number;              // 0–1; 1.0 for exact or alias match
}

/**
 * Check whether `editConcept` semantically matches any node in `contradictsNodes`.
 *
 * Layers (short-circuits on first positive):
 *   1. Exact match after normalisation
 *   2. Domain alias dictionary lookup
 *   3. Levenshtein fuzzy match (threshold = FUZZY_THRESHOLD = 0.80)
 *
 * Returns the best matching nodeId and the similarity score.
 */
export function matchesContradictsNode(
  editConcept: string,
  contradictsNodes: string[],
): ConceptMatchResult {
  if (contradictsNodes.length === 0) {
    return { matched: false, bestMatch: null, score: 0 };
  }

  const normEdit = normalizeConceptId(editConcept);

  // Build a reverse lookup from alias → canonical node ID
  // (pre-compute once if this becomes a hot path, but it's fine for study-scale use)
  const aliasLookup = new Map<string, string>();
  for (const [canonicalId, aliases] of Object.entries(DOMAIN_ALIASES)) {
    for (const alias of aliases) {
      aliasLookup.set(normalizeConceptId(alias), canonicalId);
    }
    // The canonical ID itself is its own alias
    aliasLookup.set(normalizeConceptId(canonicalId), canonicalId);
  }

  let bestNode: string | null = null;
  let bestScore = 0;

  for (const node of contradictsNodes) {
    const normNode = normalizeConceptId(node);

    // Layer 1: exact normalised match
    if (normEdit === normNode) {
      return { matched: true, bestMatch: node, score: 1.0 };
    }

    // Layer 2: alias dictionary
    const editCanonical = aliasLookup.get(normEdit);
    const nodeCanonical = aliasLookup.get(normNode) ?? normNode;
    if (editCanonical && editCanonical === nodeCanonical) {
      return { matched: true, bestMatch: node, score: 1.0 };
    }
    // Also check: the edit concept IS the canonical form of the node's alias
    const reverseMatch = aliasLookup.get(normNode);
    if (reverseMatch && reverseMatch === normEdit) {
      return { matched: true, bestMatch: node, score: 1.0 };
    }

    // Layer 3: fuzzy Levenshtein
    const ratio = similarityRatio(normEdit, normNode);
    if (ratio > bestScore) {
      bestScore = ratio;
      bestNode = node;
    }
  }

  if (bestScore >= FUZZY_THRESHOLD) {
    return { matched: true, bestMatch: bestNode, score: bestScore };
  }

  return { matched: false, bestMatch: bestNode, score: bestScore };
}
