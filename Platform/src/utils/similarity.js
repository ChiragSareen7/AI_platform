/**
 * String similarity for behavior stability (0 = different, 1 = same).
 * Uses Jaccard-like word overlap and length similarity.
 */

function normalize(str) {
  if (!str || typeof str !== 'string') return '';
  return str
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function wordSet(str) {
  const n = normalize(str);
  if (!n) return new Set();
  return new Set(n.split(' ').filter(Boolean));
}

function jaccardSimilarity(a, b) {
  const setA = wordSet(a);
  const setB = wordSet(b);
  if (setA.size === 0 && setB.size === 0) return 1;
  if (setA.size === 0 || setB.size === 0) return 0;
  let intersection = 0;
  for (const w of setA) {
    if (setB.has(w)) intersection++;
  }
  const union = setA.size + setB.size - intersection;
  return union === 0 ? 1 : intersection / union;
}

/**
 * Combined similarity: Jaccard + penalty for length difference.
 * Returns value in [0, 1].
 */
function similarity(a, b) {
  if (a === b) return 1;
  const j = jaccardSimilarity(a, b);
  const lenA = (normalize(a).length || 1);
  const lenB = (normalize(b).length || 1);
  const ratio = Math.min(lenA, lenB) / Math.max(lenA, lenB);
  const lengthFactor = 0.3 + 0.7 * ratio;
  return j * lengthFactor;
}

/**
 * Behavior stability: average pairwise similarity of response list.
 */
function behaviorStability(responses) {
  if (!Array.isArray(responses) || responses.length <= 1) return 1;
  let sum = 0;
  let count = 0;
  for (let i = 0; i < responses.length; i++) {
    for (let j = i + 1; j < responses.length; j++) {
      sum += similarity(responses[i], responses[j]);
      count++;
    }
  }
  return count === 0 ? 1 : sum / count;
}

module.exports = {
  similarity,
  behaviorStability,
  jaccardSimilarity,
};
