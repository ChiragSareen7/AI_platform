/**
 * Compares actual metrics from a query run against user preferences.
 * Returns status object: "good" | "bad" for each dimension.
 */

function compare(actualMetrics, preferences) {
  if (!preferences) {
    return {
      latencyStatus: 'good',
      accuracyStatus: 'good',
      hallucinationStatus: 'good',
      tokenStatus: 'good',
      costStatus: 'good',
    };
  }

  const system = actualMetrics?.system || {};
  const aiQuality = actualMetrics?.aiQuality || {};
  const latency = system.latency ?? 0;
  const tokenUsage = system.tokenUsage?.total ?? system.tokenUsage ?? 0;
  const costPerRequest = system.costPerRequest ?? 0;
  const accuracyScore = aiQuality.accuracyScore ?? 0;
  const hallucinationScore = aiQuality.hallucinationScore ?? 0;

  const maxLatency = preferences.maxLatency ?? 2000;
  const maxTokens = preferences.maxTokens ?? 800;
  const maxCost = preferences.maxCost ?? 0.05;
  const minAccuracy = preferences.minAccuracy ?? 0.7;
  const maxHallucination = preferences.maxHallucination ?? 0.3;

  return {
    latencyStatus: latency <= maxLatency ? 'good' : 'bad',
    accuracyStatus: accuracyScore >= minAccuracy ? 'good' : 'bad',
    hallucinationStatus: hallucinationScore <= maxHallucination ? 'good' : 'bad',
    tokenStatus: tokenUsage <= maxTokens ? 'good' : 'bad',
    costStatus: costPerRequest <= maxCost ? 'good' : 'bad',
  };
}

module.exports = {
  compare,
};
