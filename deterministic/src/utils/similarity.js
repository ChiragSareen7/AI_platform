/**
 * Similarity engine: Jaccard + Cosine (term-frequency vectors).
 * Used for context vs answer validation and consistency check.
 */

function tokenize(text) {
  if (!text || typeof text !== 'string') return [];
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean);
}

function jaccardSimilarity(text1, text2) {
  const set1 = new Set(tokenize(text1));
  const set2 = new Set(tokenize(text2));
  if (set1.size === 0 && set2.size === 0) return 1;
  if (set1.size === 0 || set2.size === 0) return 0;
  let intersection = 0;
  for (const w of set1) {
    if (set2.has(w)) intersection++;
  }
  const union = set1.size + set2.size - intersection;
  return union === 0 ? 1 : intersection / union;
}

function termFreqVector(tokens) {
  const v = {};
  for (const t of tokens) {
    v[t] = (v[t] || 0) + 1;
  }
  return v;
}

function dotProduct(a, b) {
  let sum = 0;
  for (const k of Object.keys(a)) {
    if (b[k]) sum += a[k] * b[k];
  }
  return sum;
}

function magnitude(v) {
  let sum = 0;
  for (const k of Object.keys(v)) {
    sum += v[k] * v[k];
  }
  return Math.sqrt(sum) || 1;
}

function cosineSimilarity(text1, text2) {
  const t1 = tokenize(text1);
  const t2 = tokenize(text2);
  if (t1.length === 0 && t2.length === 0) return 1;
  const v1 = termFreqVector(t1);
  const v2 = termFreqVector(t2);
  const mag1 = magnitude(v1);
  const mag2 = magnitude(v2);
  return dotProduct(v1, v2) / (mag1 * mag2);
}

/**
 * Combined score (0–1). Uses average of Jaccard and Cosine.
 */
function calculateSimilarity(text1, text2) {
  const j = jaccardSimilarity(text1, text2);
  const c = cosineSimilarity(text1, text2);
  return (j + c) / 2;
}

module.exports = {
  calculateSimilarity,
  jaccardSimilarity,
  cosineSimilarity,
  tokenize,
};
