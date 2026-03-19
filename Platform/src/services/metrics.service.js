const config = require('../config/defaultConfig');

function buildMetrics(opts = {}) {
  const {
    latency = 0,
    tokenUsage = { input: 0, output: 0, total: 0 },
    costPerRequest = 0,
    hallucinationScore = 0,
    accuracyScore = 0,
    relevanceScore = 0,
    retryRate = 0,
    errorRate = 0,
    behaviorStability = 1,
    toxicityScore = 0,
    userSatisfaction = 0.5,
  } = opts;

  return {
    system: {
      latency,
      tokenUsage,
      costPerRequest,
    },
    aiQuality: {
      hallucinationScore,
      accuracyScore,
      relevanceScore,
    },
    stability: {
      retryRate,
      errorRate,
      behaviorStability,
    },
    safety: {
      toxicityScore,
    },
    user: {
      userSatisfaction,
    },
  };
}

function computeCost(tokenUsage) {
  const { costPer1kInput, costPer1kOutput } = config;
  const inputCost = (tokenUsage.input / 1000) * costPer1kInput;
  const outputCost = (tokenUsage.output / 1000) * costPer1kOutput;
  return inputCost + outputCost;
}

function mergeWithEvaluation(metrics, evaluationResult) {
  const m = { ...metrics };
  if (evaluationResult) {
    m.aiQuality = {
      ...m.aiQuality,
      hallucinationScore: evaluationResult.hallucinationScore,
      accuracyScore: evaluationResult.accuracyScore,
      relevanceScore: evaluationResult.relevanceScore,
    };
    m.safety = { ...m.safety, toxicityScore: evaluationResult.toxicityScore };
  }
  return m;
}

function mergeStability(metrics, retryCount, errorOccurred, behaviorStability) {
  const m = { ...metrics };
  m.stability = {
    ...m.stability,
    retryRate: retryCount > 0 ? retryCount / (retryCount + 1) : 0,
    errorRate: errorOccurred ? 1 : 0,
    behaviorStability: behaviorStability ?? m.stability.behaviorStability,
  };
  return m;
}

module.exports = {
  buildMetrics,
  computeCost,
  mergeWithEvaluation,
  mergeStability,
};
