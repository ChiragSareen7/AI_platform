/**
 * Rough token estimation (chars / 4 for English).
 */

function estimateTokens(text) {
  if (!text || typeof text !== 'string') return { input: 0, output: 0 };
  const chars = text.length;
  const tokens = Math.ceil(chars / 4);
  return { input: tokens, output: 0 };
}

function estimateQueryResponseTokens(query, response) {
  const q = estimateTokens(query);
  const r = estimateTokens(response);
  return {
    input: q.input,
    output: r.input,
    total: q.input + r.input,
  };
}

module.exports = {
  estimateTokens,
  estimateQueryResponseTokens,
};
