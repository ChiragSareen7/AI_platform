/**
 * Consistency check: run same query N times, compare outputs.
 */
const { calculateSimilarity } = require('../utils/similarity');

async function runSameQueryMultipleTimes(runPipeline, query, n = 3) {
  const outputs = [];
  for (let i = 0; i < n; i++) {
    const result = await runPipeline(query);
    outputs.push(result.answer || result.finalAnswer || '');
  }
  const exactMatch = outputs.every((o) => o === outputs[0]);
  if (exactMatch) {
    return { deterministic: true, avgSimilarity: 1, outputs };
  }
  let sum = 0;
  let count = 0;
  for (let i = 0; i < outputs.length; i++) {
    for (let j = i + 1; j < outputs.length; j++) {
      sum += calculateSimilarity(outputs[i], outputs[j]);
      count++;
    }
  }
  const avgSimilarity = count > 0 ? sum / count : 0;
  return { deterministic: false, avgSimilarity, outputs };
}

module.exports = { runSameQueryMultipleTimes };
